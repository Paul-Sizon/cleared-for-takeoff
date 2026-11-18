"""Command-line entry point."""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

from . import __version__
from .checks import load_all
from .finding import BLOCKER, INFO, SEVERITY_ORDER, VALIDATOR_BLOCKING, WARNING, Finding
from .project import load
from .suppress import is_suppressed, load_rules
from . import html as html_report


def verdict(findings, has_app: bool = True) -> tuple:
    if not has_app:
        return "NO APP FOUND", "no iOS app target detected; point the scanner at the app root or a .ipa/.xcarchive"
    b = sum(f.severity == BLOCKER for f in findings)
    w = sum(f.severity == WARNING for f in findings)
    if b:
        return "NOT READY", f"{b} blocker(s) must be fixed before submission"
    if w:
        return "LIKELY READY", f"no blockers; {w} warning(s) worth fixing first"
    return "READY", "no blockers or warnings from automated checks; semantic review still required"


def conf_label(c: str) -> str:
    return "review-risk (validator-blocking if shipped as-is; needs build verification)" if c == VALIDATOR_BLOCKING else c


def run(path: str, only=None, skip=None):
    registry = load_all()
    proj = load(path)
    findings, errors, ran = [], [], []
    try:
        for cid, spec in registry.items():
            if only and cid not in only:
                continue
            if skip and cid in skip:
                continue
            if proj.is_bundle and not spec.bundle:
                continue
            if not proj.is_bundle and not spec.source:
                continue
            ran.append(spec)
            try:
                findings += spec.fn(proj)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{cid}: {e.__class__.__name__}: {e}\n{traceback.format_exc(limit=3)}")
        rules = load_rules(proj.root)
        kept, suppressed = [], []
        for f in findings:
            (suppressed if is_suppressed(f, rules, proj.root) else kept).append(f)
        # de-duplicate identical rule+location
        seen, uniq = set(), []
        for f in kept:
            key = (f.rule, f.file, f.line, f.target, f.title)
            if key not in seen:
                seen.add(key)
                uniq.append(f)
        uniq.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.check, f.file or "", f.line or 0))
        return proj, uniq, suppressed, ran, errors
    finally:
        proj.cleanup()


def to_json(proj, findings, suppressed, ran, errors) -> dict:
    v, why = verdict(findings, bool(proj.main_targets()))
    return {
        "tool": "cleared-for-takeoff", "version": __version__,
        "root": str(proj.root), "stacks": sorted(proj.stacks), "built_product": proj.is_bundle,
        "expo_managed": proj.expo_managed,
        "targets": [{"name": t.name, "kind": t.kind, "bundle_id": t.bundle_id, "info_plist": t.info_path,
                     "entitlements": t.entitlements_path, "privacy_manifests": [m[0] for m in t.manifests],
                     "version": t.version, "build": t.build, "device_family": sorted(t.device_family)}
                    for t in proj.targets],
        "verdict": v, "verdict_reason": why,
        "summary": {s: sum(f.severity == s for f in findings) for s in (BLOCKER, WARNING, INFO)},
        "checks_run": [{"id": c.id, "title": c.title, "area": c.area,
                        "findings": sum(f.check == c.id or f.check.startswith(c.id) for f in findings)} for c in ran],
        "findings": [f.to_dict() for f in findings],
        "suppressed": len(suppressed),
        "notes": proj.notes, "errors": errors,
    }


def to_text(data: dict, color: bool) -> str:
    def c(code, s):
        return f"\033[{code}m{s}\033[0m" if color else s
    sev_color = {BLOCKER: "31;1", WARNING: "33;1", INFO: "36"}
    lines = []
    v = data["verdict"]
    vc = {"NOT READY": "31;1", "LIKELY READY": "33;1", "READY": "32;1"}.get(v, "35;1")
    lines.append(c("1", "Cleared for Takeoff") + f"  ({', '.join(data['stacks']) or 'unknown stack'}"
                 + (", built product" if data["built_product"] else "") + ")")
    lines.append(f"Readiness: {c(vc, v)} - {data['verdict_reason']}")
    s = data["summary"]
    lines.append(f"{s['BLOCKER']} blocker(s) · {s['WARNING']} warning(s) · {s['INFO']} info"
                 + (f" · {data['suppressed']} suppressed" if data["suppressed"] else ""))
    lines.append("")
    lines.append(c("1", "Targets"))
    for t in data["targets"]:
        lines.append(f"  - {t['name']} [{t['kind']}] {t['bundle_id']}  v{t['version'] or '?'} ({t['build'] or '?'})  "
                     f"manifest: {'yes' if t['privacy_manifests'] else 'NO'}")
    for sev in (BLOCKER, WARNING, INFO):
        group = [f for f in data["findings"] if f["severity"] == sev]
        if not group:
            continue
        lines.append("")
        lines.append(c(sev_color[sev], f"{sev}S ({len(group)})"))
        for i, f in enumerate(group, 1):
            lines.append(f"  [{sev[0]}{i}] {f['title']}  " + c("2", f"[{f['guideline']}] {f['rule']}"))
            if f["location"]:
                lines.append(f"       at {f['location']}")
            lines.append(f"       {f['evidence']}")
            lines.append(c("32", f"       fix: {f['fix']}"))
            lines.append(c("2", f"       confidence: {conf_label(f['confidence'])}"))
    lines.append("")
    lines.append(c("1", "Checklist"))
    for chk in data["checks_run"]:
        n = sum(1 for f in data["findings"] if f["check"] == chk["id"] and f["severity"] != INFO)
        mark = c("31", "✗") if n else c("32", "✓")
        lines.append(f"  {mark} {chk['title']}" + (f": {n} issue(s)" if n else ""))
    for n in data["notes"]:
        lines.append(c("2", f"note: {n}"))
    for e in data["errors"]:
        lines.append(c("31", f"check error: {e.splitlines()[0]}"))
    lines.append("")
    lines.append(c("2", "Automated checks only. Run the skill for semantic review (metadata, 4.2/4.3, AI, UGC, "
                        "hidden features) and the external checklist. Passing never guarantees approval."))
    return "\n".join(lines)


def _recount(data: dict) -> None:
    """Recompute verdict + summary after the agent edited findings in the JSON."""
    fs = data.setdefault("findings", [])
    for f in fs:
        f.setdefault("location", f"{f['file']}:{f['line']}" if f.get("file") and f.get("line") else f.get("file") or "")
        f.setdefault("rule", f.get("check", "semantic"))
        f.setdefault("check", "semantic")
        f.setdefault("confidence", "judgment-call")
    fs.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 3), f.get("check", ""), f.get("location", "")))
    data["summary"] = {s: sum(f["severity"] == s for f in fs) for s in (BLOCKER, WARNING, INFO)}
    if data.get("verdict") != "NO APP FOUND":
        b, w = data["summary"][BLOCKER], data["summary"][WARNING]
        data["verdict"], data["verdict_reason"] = verdict([Finding(**{k: f.get(k) for k in (
            "check", "rule", "title", "severity", "confidence", "guideline", "evidence", "fix")}) for f in fs])
    data.setdefault("checks_run", [])
    data.setdefault("targets", [])
    data.setdefault("notes", [])
    data.setdefault("errors", [])
    data.setdefault("suppressed", 0)
    data.setdefault("stacks", [])
    data.setdefault("built_product", False)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="preflight", description="App Store pre-submission scanner (iOS: Swift/ObjC, React Native/Expo, Flutter).")
    ap.add_argument("path", nargs="?", default=".", help="project root, or a .app/.ipa/.xcarchive")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--only", help="comma-separated check ids")
    ap.add_argument("--skip", help="comma-separated check ids to skip")
    ap.add_argument("--ci", action="store_true", help="exit 1 if any blocker (or warning with --strict)")
    ap.add_argument("--strict", action="store_true", help="with --ci, warnings also fail")
    ap.add_argument("--html", metavar="FILE", help="also write a self-contained HTML report")
    ap.add_argument("--from-json", metavar="FILE", help="render a previously saved (or agent-enriched) JSON report instead of scanning")
    ap.add_argument("--list-checks", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    if a.list_checks:
        for cid, spec in load_all().items():
            print(f"{cid:20} {spec.area:14} {spec.title}{'  [also built products]' if spec.bundle else ''}")
        return 0
    if a.from_json:
        data = html_report.load_json(a.from_json)
        _recount(data)
    else:
        if not Path(a.path).expanduser().exists():
            print(f"path not found: {a.path}", file=sys.stderr)
            return 2
        only = set(a.only.split(",")) if a.only else None
        skip = set(a.skip.split(",")) if a.skip else None
        proj, findings, suppressed, ran, errors = run(a.path, only, skip)
        data = to_json(proj, findings, suppressed, ran, errors)
    if a.html:
        html_report.write(data, a.html)
        print(f"HTML report: {Path(a.html).resolve()}", file=sys.stderr)
    if a.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(to_text(data, color=sys.stdout.isatty() and not a.no_color))
    if a.ci:
        if data["summary"][BLOCKER] or (a.strict and data["summary"][WARNING]):
            return 1
    return 0
