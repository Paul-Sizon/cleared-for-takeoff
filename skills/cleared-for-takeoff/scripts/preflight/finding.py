"""Finding model shared by every check."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

BLOCKER = "BLOCKER"   # will be rejected (or blocked at upload) if shipped as-is
WARNING = "WARNING"   # likely rejection / reviewers commonly flag it
INFO = "INFO"         # best practice, or something to verify by hand

SEVERITY_ORDER = {BLOCKER: 0, WARNING: 1, INFO: 2}

# Confidence vocabulary (see references/report-format.md):
#   validator-certain  - Apple's automated upload validation will block it, AND the evidence
#                        comes from a built product (.app/.ipa/.xcarchive).
#   validator-blocking - same mechanical gate, but evidence is source/config only; needs
#                        build verification. Reported as
#                        "review-risk (validator-blocking if shipped as-is)".
#   review-risk        - pattern human reviewers reject frequently; well evidenced.
#   judgment-call      - semantic assessment; a reasonable reviewer could go either way.
VALIDATOR_CERTAIN = "validator-certain"
VALIDATOR_BLOCKING = "validator-blocking"
REVIEW_RISK = "review-risk"
JUDGMENT = "judgment-call"


@dataclass
class Finding:
    check: str                 # check id, e.g. "privacy-strings"
    rule: str                  # stable rule id, e.g. "privacy-strings/missing-key"
    title: str
    severity: str
    confidence: str
    guideline: str             # e.g. "5.1.1(ii)" or "ITMS-91053"
    evidence: str
    fix: str
    file: Optional[str] = None
    line: Optional[int] = None
    target: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def location(self) -> str:
        if not self.file:
            return ""
        return f"{self.file}:{self.line}" if self.line else self.file

    def to_dict(self) -> dict:
        d = asdict(self)
        d["location"] = self.location()
        return d
