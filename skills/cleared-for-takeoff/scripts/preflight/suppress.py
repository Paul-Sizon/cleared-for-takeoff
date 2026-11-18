"""Suppressions: `.preflightignore` file and inline `preflight:ignore <rule>` comments.

.preflightignore format (one per line, # comments):
    privacy-strings/vague                  # suppress a rule everywhere
    content/other-platform  src/legal/*    # suppress a rule for matching paths
    secrets                                # suppress a whole check
"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

INLINE = re.compile(r"preflight:ignore(?:\s+([\w\-/,]+))?")


def load_rules(root: Path) -> list:
    rules = []
    f = root / ".preflightignore"
    if not f.exists():
        return rules
    for line in f.read_text(errors="ignore").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        rules.append((parts[0], parts[1] if len(parts) > 1 else None))
    return rules


def _match_rule(pattern: str, finding) -> bool:
    return pattern in (finding.rule, finding.check) or fnmatch.fnmatch(finding.rule, pattern)


def is_suppressed(finding, rules: list, root: Path) -> bool:
    for pattern, glob in rules:
        if _match_rule(pattern, finding) and (glob is None or (finding.file and fnmatch.fnmatch(finding.file, glob))):
            return True
    if finding.file and finding.line:
        try:
            lines = (root / finding.file).read_text(errors="ignore").splitlines()
        except OSError:
            return False
        for ln in (finding.line - 1, finding.line - 2):
            if 0 <= ln < len(lines):
                m = INLINE.search(lines[ln])
                if m and (not m.group(1) or any(_match_rule(p, finding) for p in m.group(1).split(","))):
                    return True
    return False
