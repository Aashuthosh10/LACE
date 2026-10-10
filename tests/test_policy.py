import pytest

from lace.patches.policy import validate_target_path


@pytest.mark.parametrize(
    "path",
    [
        "../outside.py",
        "/etc/passwd",
        "C:/Windows/system.ini",
        r"src\outside.py",
        ".git/config",
        "config/.env",
        "secrets/private.key",
        ".lace/policy/rules.json",
    ],
)
def test_rejects_forbidden_paths(path: str) -> None:
    assert validate_target_path(path)


@pytest.mark.parametrize("path", ["src/lace/app.py", "tests/test_app.py", "docs/design.md"])
def test_allows_normal_repository_paths(path: str) -> None:
    assert validate_target_path(path) == ()
