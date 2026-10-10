import pytest

from lace.patches.parser import PatchParseError, parse_unified_diff


def parse(text: str):
    return parse_unified_diff(text, max_bytes=10_000, max_files=10, max_changed_lines=100)


def test_parses_valid_patch(valid_patch: str) -> None:
    result = parse(valid_patch)
    assert result.targets == ("calculator.py",)
    assert (result.additions, result.deletions) == (2, 0)


@pytest.mark.parametrize(
    "patch",
    [
        "",
        "not a patch",
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n",
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ broken @@\n+x\n",
        "diff --git a/x.bin b/x.bin\nGIT binary patch\n",
    ],
)
def test_rejects_malformed_patch(patch: str) -> None:
    with pytest.raises(PatchParseError):
        parse(patch)


def test_rejects_conflicting_headers() -> None:
    patch = """diff --git a/x.py b/x.py
--- a/y.py
+++ b/x.py
@@ -1 +1 @@
-a
+b
"""
    with pytest.raises(PatchParseError, match="conflicts"):
        parse(patch)
