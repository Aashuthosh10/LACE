from lace.patches import assess_patch
from lace.risk import score_patch


def patch_for(path: str, added: str = "value = 1") -> str:
    return f"""diff --git a/{path} b/{path}
--- a/{path}
+++ b/{path}
@@ -1 +1,2 @@
 old = 1
+{added}
"""


def test_risk_score_is_deterministic_and_explainable() -> None:
    patch = patch_for("pyproject.toml", "subprocess.run(['tool'])")
    assessment = assess_patch(patch)
    first = score_patch(assessment, patch)
    second = score_patch(assessment, patch)
    assert first == second
    assert first.level == "high"
    assert {finding.rule_id for finding in first.findings} >= {
        "RISK-DEPENDENCY",
        "RISK-CONFIG",
        "RISK-COMMAND",
    }
    assert first.advisory_only


def test_large_deletion_increases_risk() -> None:
    removed = "\n".join(f"-line {number}" for number in range(20))
    patch = f"""diff --git a/src/data.py b/src/data.py
--- a/src/data.py
+++ b/src/data.py
@@ -1,20 +1 @@
{removed}
+remaining
"""
    risk = score_patch(assess_patch(patch), patch)
    assert any(finding.rule_id == "RISK-LARGE-DELETION" for finding in risk.findings)
    assert risk.score >= 20


def test_low_risk_does_not_change_policy_decision() -> None:
    patch = patch_for(".env")
    assessment = assess_patch(patch)
    risk = score_patch(assessment, patch)
    assert not assessment.policy_allowed
    assert risk.advisory_only
