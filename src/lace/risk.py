"""Deterministic advisory patch-risk scoring."""

import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any, Literal

from lace.patches.assessment import PatchAssessment

RiskLevel = Literal["low", "moderate", "high"]

_DEPENDENCY_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
}
_CONFIG_SUFFIXES = {".toml", ".ini", ".cfg", ".yaml", ".yml", ".json"}
_SECURITY_TERMS = {"auth", "security", "crypto", "permission", "credential", "secret"}
_SUSPICIOUS = re.compile(
    r"(?:subprocess\.|os\.system\(|shell\s*=\s*True|\beval\(|\bexec\(|rm\s+-rf|"
    r"powershell|cmd\.exe|curl\s+|wget\s+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RiskFinding:
    rule_id: str
    points: int
    reason: str


@dataclass(frozen=True)
class RiskAssessment:
    score: int
    level: RiskLevel
    findings: tuple[RiskFinding, ...]
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "advisory_only": self.advisory_only,
            "findings": [asdict(finding) for finding in self.findings],
        }


def score_patch(assessment: PatchAssessment, patch_text: str) -> RiskAssessment:
    """Return explainable, version-one advisory risk; policy remains authoritative."""
    if assessment.patch is None:
        return RiskAssessment(100, "high", (RiskFinding("RISK-INVALID", 100, "invalid patch"),))

    info = assessment.patch
    findings: list[RiskFinding] = []
    names = [PurePosixPath(target).name.casefold() for target in info.targets]
    if any(name in _DEPENDENCY_FILES for name in names):
        findings.append(RiskFinding("RISK-DEPENDENCY", 20, "dependency metadata changes"))
    if any(PurePosixPath(name).suffix in _CONFIG_SUFFIXES for name in names):
        findings.append(RiskFinding("RISK-CONFIG", 10, "configuration files change"))
    if any(any(term in target.casefold() for term in _SECURITY_TERMS) for target in info.targets):
        findings.append(RiskFinding("RISK-SECURITY", 15, "security-related path changes"))
    if len(info.targets) > 3:
        points = min(20, (len(info.targets) - 3) * 2)
        findings.append(RiskFinding("RISK-FILE-COUNT", points, f"{len(info.targets)} files change"))
    changed = info.additions + info.deletions
    if changed >= 50:
        findings.append(
            RiskFinding("RISK-CHANGE-SIZE", min(20, changed // 50), f"{changed} changed lines")
        )
    if info.deletions >= 20 and info.deletions / max(changed, 1) >= 0.7:
        findings.append(
            RiskFinding("RISK-LARGE-DELETION", 20, "deletions are at least 70% of the patch")
        )
    if info.deletions >= 100:
        findings.append(RiskFinding("RISK-DELETION-VOLUME", 15, "at least 100 lines deleted"))
    added_text = "\n".join(line[1:] for line in patch_text.splitlines() if line.startswith("+"))
    if _SUSPICIOUS.search(added_text):
        findings.append(
            RiskFinding("RISK-COMMAND", 25, "command execution or dynamic evaluation text added")
        )

    score = min(100, sum(finding.points for finding in findings))
    level: RiskLevel = "high" if score >= 50 else "moderate" if score >= 25 else "low"
    return RiskAssessment(score, level, tuple(findings))
