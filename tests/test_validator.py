import hashlib
import subprocess
from pathlib import Path

from lace.patches.validator import validate_patch


def digest(repository: Path) -> str:
    value = hashlib.sha256()
    for path in sorted(repository.rglob("*")):
        if path.is_file():
            value.update(path.relative_to(repository).as_posix().encode())
            value.update(path.read_bytes())
    return value.hexdigest()


def status(repository: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_validates_in_copy_and_preserves_original(git_repository: Path, valid_patch: str) -> None:
    before_digest = digest(git_repository)
    before_status = status(git_repository)

    result = validate_patch(git_repository, valid_patch)

    assert result.allowed
    assert result.policy_allowed
    assert result.applicable
    assert result.original_unchanged
    assert digest(git_repository) == before_digest
    assert status(git_repository) == before_status
    assert "divisor == 0" not in (git_repository / "calculator.py").read_text(encoding="utf-8")


def test_rejects_non_applicable_patch(git_repository: Path, valid_patch: str) -> None:
    (git_repository / "calculator.py").write_text("different\n", encoding="utf-8")
    before = digest(git_repository)
    result = validate_patch(git_repository, valid_patch)
    assert not result.allowed
    assert result.policy_allowed
    assert not result.applicable
    assert result.original_unchanged
    assert digest(git_repository) == before


def test_rejects_forbidden_target_before_git(git_repository: Path) -> None:
    patch = """diff --git a/.env b/.env
--- /dev/null
+++ b/.env
@@ -0,0 +1 @@
+SECRET=value
"""
    result = validate_patch(git_repository, patch)
    assert not result.allowed
    assert not result.policy_allowed
    assert not result.applicable
    assert any("sensitive" in error for error in result.errors)


def test_rejects_non_git_directory(tmp_path: Path, valid_patch: str) -> None:
    result = validate_patch(tmp_path, valid_patch)
    assert not result.allowed
    assert "Git work tree" in result.errors[0]
