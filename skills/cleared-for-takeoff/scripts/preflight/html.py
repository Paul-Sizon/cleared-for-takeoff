"""Self-contained HTML report (no external assets). Input: the JSON produced by cli.to_json,
optionally enriched by the agent (semantic findings, summary, review notes, not_checked…)."""
from __future__ import annotations

import html
import json
import re
from collections import OrderedDict
from datetime import date

SEV = ("BLOCKER", "WARNING", "INFO")
SEV_LABEL = {"BLOCKER": "Blockers", "WARNING": "Warnings", "INFO": "Info"}
CONF_LABEL = {
    "validator-certain": ("Validator-certain", "Apple's upload validation blocks this; seen in the built product."),
    "validator-blocking": ("Upload-blocking", "Upload validation would block this; evidence is from source, so verify with a build."),
    "review-risk": ("Review risk", "A pattern App Review rejects often."),
    "judgment-call": ("Judgment call", "A reasonable reviewer could go either way."),
}
FLIGHT_STATUS = {"NOT READY": "Grounded", "LIKELY READY": "Holding short", "READY": "Cleared for takeoff",
                 "READY TO SUBMIT": "Cleared for takeoff", "NO APP FOUND": "No aircraft found"}
VERDICT_CLASS = {"NOT READY": "bad", "LIKELY READY": "warn", "READY": "good", "READY TO SUBMIT": "good"}
DEFAULT_NOT_CHECKED = [
    "Runtime crashes and broken flows on a real device",
    "Live server content, feature flags and backend availability",
    "In-app purchase sandbox behaviour and restore",
    "Push delivery, OAuth and deep links",
    "Screenshots, creative assets and App Store Connect answers (unless provided)",
]

e = html.escape


def rich(text) -> str:
    """Escape, then turn `backticks` into <code>."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(str(text or "")))


def _verdict(data) -> tuple:
    if data.get("verdict") == "NO APP FOUND":
        return data["verdict"], data.get("verdict_reason", "")
    b = sum(f["severity"] == "BLOCKER" for f in data["findings"])
    w = sum(f["severity"] == "WARNING" for f in data["findings"])
    if b:
        return "NOT READY", f"{b} blocker{'s' if b != 1 else ''} must be fixed before submission"
    if w:
        return "LIKELY READY", f"No blockers. {w} warning{'s' if w != 1 else ''} worth fixing first"
    return "READY", "No blockers or warnings found. Not a guarantee of approval"


def _areas(data) -> "OrderedDict":
    areas = OrderedDict()
    check_area = {c["id"]: c["area"] for c in data.get("checks_run", [])}
    for c in data.get("checks_run", []):
        areas.setdefault(c["area"], {"BLOCKER": 0, "WARNING": 0, "INFO": 0, "checks": []})["checks"].append(c["title"])
    for f in data["findings"]:
        area = f.get("area") or check_area.get(f["check"]) or "Reviewer judgment"
        areas.setdefault(area, {"BLOCKER": 0, "WARNING": 0, "INFO": 0, "checks": []})[f["severity"]] += 1
    return areas


def _donut(counts: dict) -> str:
    total = sum(counts.values())
    if not total:
        return ('<svg viewBox="0 0 42 42" class="donut" role="img" aria-label="No issues">'
                '<circle cx="21" cy="21" r="15.9" class="ring-bg"/>'
                '<circle cx="21" cy="21" r="15.9" class="seg good" stroke-dasharray="100 0"/>'
                '<text x="21" y="23.5" class="donut-num">0</text></svg>')
    parts, offset = [], 25
    for s in SEV:
        pct = counts[s] / total * 100
        if pct:
            parts.append(f'<circle cx="21" cy="21" r="15.9" class="seg {s.lower()}" '
                         f'stroke-dasharray="{pct:.2f} {100 - pct:.2f}" stroke-dashoffset="{offset:.2f}"/>')
            offset -= pct
    return (f'<svg viewBox="0 0 42 42" class="donut" role="img" aria-label="{total} findings">'
            f'<circle cx="21" cy="21" r="15.9" class="ring-bg"/>{"".join(parts)}'
            f'<text x="21" y="23.5" class="donut-num">{total}</text></svg>')


def _finding(f: dict, idx: str) -> str:
    sev = f["severity"]
    conf = CONF_LABEL.get(f.get("confidence", ""), (f.get("confidence", ""), ""))
    loc = f.get("location") or ""
    meta = []
    if f.get("guideline"):
        meta.append(f'<span class="chip gl" title="App Review Guideline / upload error">{e(f["guideline"])}</span>')
    meta.append(f'<span class="chip conf conf-{e(f.get("confidence", ""))}" title="{e(conf[1])}">{e(conf[0])}</span>')
    if f.get("target"):
        meta.append(f'<span class="chip tgt">target · {e(f["target"])}</span>')
    if f.get("check") == "semantic" or f.get("source") == "reviewer":
        meta.append('<span class="chip rev">reviewer judgment</span>')
    search = " ".join(str(f.get(k, "")) for k in ("title", "evidence", "fix", "rule", "guideline", "location", "target")).lower()
    return f'''
<details class="finding {sev.lower()}" data-sev="{sev}" data-search="{e(search)}" {"open" if sev != "INFO" else ""}>
  <summary>
    <span class="sev-dot" aria-hidden="true"></span>
    <span class="fid">{idx}</span>
    <span class="ftitle">{e(f["title"])}</span>
    <span class="fmeta">{"".join(meta)}</span>
  </summary>
  <div class="fbody">
    {f'<div class="loc"><span>Where</span><code>{e(loc)}</code></div>' if loc else ""}
    <div class="row"><span>Evidence</span><p>{rich(f.get("evidence", ""))}</p></div>
    {f'<div class="row"><span>Why</span><p>{rich(f["why"])}</p></div>' if f.get("why") else ""}
    <div class="row fix"><span>Fix</span><p>{rich(f.get("fix", ""))}</p></div>
    <div class="rule">{e(f.get("rule", ""))}</div>
  </div>
</details>'''


def render(data: dict) -> str:
    verdict, reason = _verdict(data)
    vclass = VERDICT_CLASS.get(verdict, "neutral")
    counts = {s: sum(f["severity"] == s for f in data["findings"]) for s in SEV}
    areas = _areas(data)
    app_name = data.get("app_name") or next((t["name"] for t in data.get("targets", []) if t["kind"] == "app"), "App")
    app_t = next((t for t in data.get("targets", []) if t["kind"] == "app"), {})
    version = f'v{app_t.get("version")} ({app_t.get("build")})' if app_t.get("version") else ""
    generated = data.get("generated") or date.today().isoformat()

    # area bars
    max_area = max([sum(a[s] for s in SEV) for a in areas.values()] + [1])
    area_rows = []
    for name, a in sorted(areas.items(), key=lambda kv: (-kv[1]["BLOCKER"], -kv[1]["WARNING"], -kv[1]["INFO"], kv[0])):
        tot = sum(a[s] for s in SEV)
        status = "bad" if a["BLOCKER"] else "warn" if a["WARNING"] else "good"
        icon = {"bad": "✕", "warn": "!", "good": "✓"}[status]
        segs = "".join(f'<i class="{s.lower()}" style="width:{a[s] / max_area * 100:.1f}%" title="{a[s]} {SEV_LABEL[s].lower()}"></i>'
                       for s in SEV if a[s])
        label = (", ".join(f"{a[s]} {SEV_LABEL[s].lower().rstrip('s') if a[s] == 1 else SEV_LABEL[s].lower()}"
                           for s in SEV if a[s]) or "Passed")
        area_rows.append(f'''<li class="area {status}"><span class="aicon">{icon}</span><span class="aname">{e(name)}</span>
  <span class="abar">{segs or '<i class="pass" style="width:100%"></i>'}</span><span class="acount">{label}</span></li>''')

    # targets
    trows = []
    for t in data.get("targets", []):
        if t["kind"] == "test":
            continue
        man = '<span class="ok">✓ present</span>' if t.get("privacy_manifests") else '<span class="no">✕ missing</span>'
        trows.append(f'<tr><td><b>{e(t["name"])}</b></td><td><span class="kind">{e(t["kind"])}</span></td>'
                     f'<td><code>{e(t.get("bundle_id") or "—")}</code></td><td>{e(t.get("version") or "—")} ({e(t.get("build") or "—")})</td>'
                     f'<td>{man}</td></tr>')

    # findings
    groups = []
    for s in SEV:
        fs = [f for f in data["findings"] if f["severity"] == s]
        if not fs:
            continue
        cards = "".join(_finding(f, f"{s[0]}{i}") for i, f in enumerate(fs, 1))
        groups.append(f'<section class="group" data-group="{s}"><h3 class="gh {s.lower()}">{SEV_LABEL[s]} <span>{len(fs)}</span></h3>{cards}</section>')
    if not groups:
        groups.append('<p class="empty">No findings. Still run the reviewer checks below before you submit.</p>')

    not_checked = data.get("not_checked") or DEFAULT_NOT_CHECKED
    extra_sections = []
    summary_html = (f'<section class="card summary"><h2>Summary</h2><p>{rich(data["summary_text"])}</p></section>'
                    if data.get("summary_text") else "")
    if data.get("review_notes"):
        extra_sections.append(f'<section class="card"><h2>Draft App Review notes</h2><pre class="notes">{e(data["review_notes"])}</pre>'
                              '<button class="copy" data-copy=".notes">Copy</button></section>')
    checklist = data.get("external_checklist") or []
    if checklist:
        items = "".join(f'<li><label><input type="checkbox"> {e(x)}</label></li>' for x in checklist)
        extra_sections.append(f'<section class="card"><h2>Before you press Submit</h2><ul class="todo">{items}</ul></section>')
    notes = data.get("notes", []) + ([data["verification_note"]] if data.get("verification_note") else [])

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Preflight · {e(app_name)}</title>
<style>{CSS}</style></head>
<body>
<main>
<header class="top">
  <div class="brand"><span class="logo">✈︎</span> Cleared for Takeoff</div>
  <div class="meta">{e(", ".join(data.get("stacks", [])) or "—")}{" · built product" if data.get("built_product") else ""} · {e(generated)} · v{e(data.get("version", ""))}
    <button class="theme" title="Toggle light/dark" aria-label="Toggle light or dark theme">◐</button></div>
</header>

<section class="hero {vclass}">
  <div class="hero-main">
    <div class="app">{e(app_name)} <span>{e(version)}</span></div>
    <div class="status">✈︎ {e(FLIGHT_STATUS.get(verdict, ""))}</div>
    <div class="verdict">{e(verdict)}</div>
    <div class="reason">{e(reason)}</div>
  </div>
  <div class="hero-stats">
    {_donut(counts)}
    <ul class="legend">
      {"".join(f'<li class="{s.lower()}"><b>{counts[s]}</b> {SEV_LABEL[s]}</li>' for s in SEV)}
    </ul>
  </div>
</section>

{summary_html}

<div class="grid">
  <section class="card"><h2>Areas checked</h2><ul class="areas">{"".join(area_rows)}</ul></section>
  <section class="card"><h2>Targets</h2>
    <table class="targets"><thead><tr><th>Target</th><th>Kind</th><th>Bundle ID</th><th>Version</th><th>Manifest</th></tr></thead>
    <tbody>{"".join(trows) or '<tr><td colspan="5">No targets found</td></tr>'}</tbody></table>
    <p class="hint">Every app extension is its own bundle and needs its own privacy manifest.</p>
  </section>
</div>

<section class="card findings">
  <div class="fhead"><h2>Findings</h2>
    <div class="filters" role="group" aria-label="Filter by severity">
      <button class="f on" data-f="ALL">All <span>{len(data["findings"])}</span></button>
      {"".join(f'<button class="f {s.lower()}" data-f="{s}">{SEV_LABEL[s]} <span>{counts[s]}</span></button>' for s in SEV)}
    </div>
    <input class="search" type="search" placeholder="Search findings, files, guidelines…" aria-label="Search findings">
  </div>
  {"".join(groups)}
</section>

{"".join(extra_sections)}

<div class="grid">
  <section class="card"><h2>Not checked by this report</h2><ul class="plain">{"".join(f"<li>{e(x)}</li>" for x in not_checked)}</ul></section>
  <section class="card"><h2>How to read confidence</h2><dl class="conf-legend">
    {"".join(f'<dt><span class="chip conf conf-{k}">{v[0]}</span></dt><dd>{v[1]}</dd>' for k, v in CONF_LABEL.items())}
  </dl></section>
</div>

{f'<section class="card"><h2>Notes</h2><ul class="plain">{"".join(f"<li>{e(n)}</li>" for n in notes)}</ul></section>' if notes else ""}

<footer>Generated by cleared-for-takeoff. Automated and reviewer checks reduce known risks; they never guarantee approval.</footer>
</main>
<script>{JS}</script>
</body></html>'''


CSS = r"""
:root{--bg:#f6f7f9;--card:#fff;--ink:#101828;--muted:#5d6b82;--line:#e4e7ec;--soft:#f2f4f7;
--blocker:#d92d20;--blocker-bg:#fef3f2;--warning:#c4610a;--warning-bg:#fffaeb;--info:#1570ef;--info-bg:#eff8ff;
--good:#079455;--good-bg:#ecfdf3;--fix:#067647;--code:#344054;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0c111d;--card:#161b26;--ink:#f5f5f6;--muted:#94969c;--line:#2a303c;--soft:#1f242f;
--blocker:#f97066;--blocker-bg:#2b1517;--warning:#fdb022;--warning-bg:#2a2112;--info:#53b1fd;--info-bg:#102a43;
--good:#47cd89;--good-bg:#0f2a1d;--fix:#75e0a7;--code:#cecfd2;color-scheme:dark}}
:root[data-theme=dark]{--bg:#0c111d;--card:#161b26;--ink:#f5f5f6;--muted:#94969c;--line:#2a303c;--soft:#1f242f;
--blocker:#f97066;--blocker-bg:#2b1517;--warning:#fdb022;--warning-bg:#2a2112;--info:#53b1fd;--info-bg:#102a43;
--good:#47cd89;--good-bg:#0f2a1d;--fix:#75e0a7;--code:#cecfd2;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Inter,Roboto,sans-serif}
main{max-width:1120px;margin:0 auto;padding:24px 16px 48px}
code,pre{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:13px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.brand{font-weight:700;letter-spacing:-.01em}.logo{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:8px;background:var(--ink);color:var(--bg);margin-right:6px}
.meta{color:var(--muted);font-size:13px;display:flex;align-items:center;gap:10px}
.theme{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;width:30px;height:30px;cursor:pointer;font-size:14px}
.hero{display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap;padding:28px;border-radius:20px;border:1px solid var(--line);background:var(--card);position:relative;overflow:hidden}
.hero:before{content:"";position:absolute;inset:0 auto 0 0;width:6px;background:var(--muted)}
.hero.bad:before{background:var(--blocker)}.hero.warn:before{background:var(--warning)}.hero.good:before{background:var(--good)}
.hero.bad{background:linear-gradient(90deg,var(--blocker-bg),var(--card) 60%)}.hero.warn{background:linear-gradient(90deg,var(--warning-bg),var(--card) 60%)}.hero.good{background:linear-gradient(90deg,var(--good-bg),var(--card) 60%)}
.app{font-size:14px;color:var(--muted);font-weight:600}.app span{font-weight:400}
.verdict{font-size:40px;font-weight:800;letter-spacing:-.02em;line-height:1.1;margin:4px 0}
.bad .verdict{color:var(--blocker)}.warn .verdict{color:var(--warning)}.good .verdict{color:var(--good)}
.reason{color:var(--muted)}
.status{display:inline-block;margin-top:10px;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:3px 10px;border-radius:99px;background:var(--soft);color:var(--muted)}
.bad .status{background:var(--blocker-bg);color:var(--blocker)}.warn .status{background:var(--warning-bg);color:var(--warning)}.good .status{background:var(--good-bg);color:var(--good)}
.hero-stats{display:flex;align-items:center;gap:20px}
.donut{width:120px;height:120px;transform:rotate(0)}.ring-bg{fill:none;stroke:var(--soft);stroke-width:5}
.seg{fill:none;stroke-width:5}.seg.blocker{stroke:var(--blocker)}.seg.warning{stroke:var(--warning)}.seg.info{stroke:var(--info)}.seg.good{stroke:var(--good)}
.donut-num{font-size:10px;font-weight:800;text-anchor:middle;fill:var(--ink)}
.legend{list-style:none;margin:0;padding:0;display:grid;gap:6px}.legend li{display:flex;align-items:center;gap:8px;color:var(--muted)}
.legend li:before{content:"";width:10px;height:10px;border-radius:3px;background:currentColor}
.legend li.blocker{color:var(--blocker)}.legend li.warning{color:var(--warning)}.legend li.info{color:var(--info)}.legend b{color:var(--ink);min-width:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}.summary p{margin:0}@media(max-width:860px){.grid{grid-template-columns:1fr}.verdict{font-size:32px}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin-top:16px}.grid .card{margin-top:0}
h2{font-size:16px;margin:0 0 12px;letter-spacing:-.01em}
.areas{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.area{display:grid;grid-template-columns:22px 140px 1fr 150px;align-items:center;gap:10px;font-size:14px}
.aicon{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;font-size:12px;font-weight:800;color:#fff}
.area.bad .aicon{background:var(--blocker)}.area.warn .aicon{background:var(--warning)}.area.good .aicon{background:var(--good)}
.abar{display:flex;height:10px;border-radius:99px;background:var(--soft);overflow:hidden}.abar i{display:block;height:100%}
.abar i.blocker{background:var(--blocker)}.abar i.warning{background:var(--warning)}.abar i.info{background:var(--info)}.abar i.pass{background:var(--good);opacity:.25}
.acount{color:var(--muted);font-size:12px;white-space:nowrap;text-align:right}
@media(max-width:520px){.area{grid-template-columns:22px 1fr 90px}.acount{display:none}}
table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;color:var(--muted);font-weight:600;border-bottom:1px solid var(--line);padding:6px 8px}
td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}td code{overflow-wrap:anywhere}.kind{background:var(--soft);padding:2px 8px;border-radius:99px;font-size:12px}
.ok{color:var(--good);font-weight:600}.no{color:var(--blocker);font-weight:600}.hint{color:var(--muted);font-size:12px;margin:10px 0 0}
.fhead{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px}.fhead h2{margin:0;margin-right:auto}
.filters{display:flex;gap:6px;flex-wrap:wrap}.f{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:5px 12px;font:inherit;font-size:13px;cursor:pointer}
.f span{color:var(--muted);margin-left:2px}.f.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}.f.on span{color:inherit;opacity:.7}
.search{flex:1 1 220px;max-width:320px;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:10px;padding:7px 12px;font:inherit;font-size:13px}
.gh{font-size:13px;text-transform:uppercase;letter-spacing:.06em;margin:20px 0 8px;display:flex;gap:8px;align-items:center}
.gh span{background:currentColor;border-radius:99px;padding:0 8px;font-size:12px}.gh span{color:var(--card)}
.gh.blocker{color:var(--blocker)}.gh.warning{color:var(--warning)}.gh.info{color:var(--info)}
.gh.blocker span{background:var(--blocker)}.gh.warning span{background:var(--warning)}.gh.info span{background:var(--info)}
.finding{border:1px solid var(--line);border-left:4px solid var(--muted);border-radius:12px;margin:8px 0;background:var(--card)}
.finding.blocker{border-left-color:var(--blocker)}.finding.warning{border-left-color:var(--warning)}.finding.info{border-left-color:var(--info)}
.finding summary{list-style:none;cursor:pointer;display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:12px 14px}
.finding summary::-webkit-details-marker{display:none}
.sev-dot{width:8px;height:8px;border-radius:50%;background:var(--muted)}.blocker .sev-dot{background:var(--blocker)}.warning .sev-dot{background:var(--warning)}.info .sev-dot{background:var(--info)}
.fid{font:600 12px ui-monospace,Menlo,monospace;color:var(--muted)}.ftitle{font-weight:600;flex:1 1 300px}
.fmeta{display:flex;gap:6px;flex-wrap:wrap}
.chip{font-size:11.5px;padding:2px 8px;border-radius:99px;background:var(--soft);color:var(--muted);white-space:nowrap}
.chip.gl{font-family:ui-monospace,Menlo,monospace;color:var(--ink)}
.conf-validator-certain,.conf-validator-blocking{background:var(--blocker-bg);color:var(--blocker)}.conf-review-risk{background:var(--warning-bg);color:var(--warning)}
.conf-judgment-call{background:var(--info-bg);color:var(--info)}.chip.rev{background:var(--info-bg);color:var(--info)}
.fbody{padding:0 14px 14px 34px;display:grid;gap:8px}
.fbody .row,.fbody .loc{display:grid;grid-template-columns:72px 1fr;gap:10px;align-items:baseline}
.fbody span{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}
.fbody p{margin:0}.fbody p code{background:var(--soft);padding:1px 5px;border-radius:5px;font-size:12.5px;color:var(--code)}.loc code{background:var(--soft);padding:2px 8px;border-radius:6px;color:var(--code);word-break:break-all}
.row.fix p{color:var(--fix);font-weight:500}.rule{font:12px ui-monospace,Menlo,monospace;color:var(--muted)}
.empty{color:var(--muted)}.plain{margin:0;padding-left:18px;color:var(--muted)}.plain li{margin:4px 0}
.conf-legend{display:grid;grid-template-columns:auto 1fr;gap:8px 12px;margin:0;align-items:center}.conf-legend dd{margin:0;color:var(--muted);font-size:13px}
.notes{white-space:pre-wrap;background:var(--soft);padding:14px;border-radius:10px;margin:0}
.copy{margin-top:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:5px 12px;cursor:pointer;font:inherit;font-size:13px}
.todo{list-style:none;padding:0;margin:0;display:grid;gap:6px}
footer{color:var(--muted);font-size:12px;text-align:center;margin-top:28px}
.hidden{display:none!important}
@media print{.filters,.search,.copy{display:none}.finding{break-inside:avoid}details.finding:not([open]) .fbody{display:grid}}
"""

JS = r"""
(()=>{const r=document.documentElement,u=new URLSearchParams(location.search).get('theme');
let saved=null;try{saved=localStorage.getItem('asp-theme')}catch(e){}
if(u||saved)r.dataset.theme=u||saved;
const tb=document.querySelector('.theme');tb&&tb.addEventListener('click',()=>{const dark=r.dataset.theme?r.dataset.theme==='dark':matchMedia('(prefers-color-scheme: dark)').matches;
r.dataset.theme=dark?'light':'dark';try{localStorage.setItem('asp-theme',r.dataset.theme)}catch(e){}});
let sev='ALL',q='';const cards=[...document.querySelectorAll('.finding')];
function apply(){cards.forEach(c=>{const show=(sev==='ALL'||c.dataset.sev===sev)&&(!q||c.dataset.search.includes(q));c.classList.toggle('hidden',!show)});
document.querySelectorAll('.group').forEach(g=>g.classList.toggle('hidden',!g.querySelector('.finding:not(.hidden)')))}
document.querySelectorAll('.f').forEach(b=>b.addEventListener('click',()=>{sev=b.dataset.f;document.querySelectorAll('.f').forEach(x=>x.classList.toggle('on',x===b));apply()}));
const s=document.querySelector('.search');s&&s.addEventListener('input',()=>{q=s.value.trim().toLowerCase();apply()});
document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{const t=document.querySelector(b.dataset.copy);
try{navigator.clipboard.writeText(t.textContent);b.textContent='Copied'}catch(e){}}));})();
"""


def write(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(data))


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
