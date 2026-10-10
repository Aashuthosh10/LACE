import hashlib
import subprocess
from pathlib import Path

import pytest

import lace.workspace.processor as processor_module
from lace.config import PatchLimits, Settings, WorkspaceLimits
from lace.workspace import PatchProcessor, WorkspaceManager


def state(repository: Path) -> tuple[str, str]:
    status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    digest = hashlib.sha256()
    for path in sorted(repository.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            digest.update(path.relative_to(repository).as_posix().encode())
            digest.update(path.read_bytes())
    return status, digest.hexdigest()


def test_applies_in_workspace_cleans_up_and_preserves_original(
    git_repository: Path, valid_patch: str
) -> None:
    before = state(git_repository)
    result = PatchProcessor().process(git_repository, valid_patch)
    assert result.status == "applied", result
    assert result.applied and result.applicable and result.policy_allowed
    assert result.changed_files == ("calculator.py",)
    assert result.original_unchanged
    assert result.workspace_created and result.workspace_cleaned
    assert state(git_repository) == before
    assert "divisor == 0" not in (git_repository / "calculator.py").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "patch",
    [
        "not a patch",
        "diff --git a/.env b/.env\n--- /dev/null\n+++ b/.env\n@@ -0,0 +1 @@\n+x=1\n",
        "diff --git a/../x.py b/../x.py\n--- a/../x.py\n+++ b/../x.py\n@@ -1 +1 @@\n-a\n+b\n",
        "diff --git a/..\\x.py b/..\\x.py\n--- a/..\\x.py\n+++ b/..\\x.py\n@@ -1 +1 @@\n-a\n+b\n",
        "diff --git a/C:/x.py b/C:/x.py\n--- a/C:/x.py\n+++ b/C:/x.py\n@@ -1 +1 @@\n-a\n+b\n",
        (
            "diff --git a/x b/x\nnew file mode 120000\n--- /dev/null\n+++ b/x\n"
            "@@ -0,0 +1 @@\n+target\n"
        ),
        "diff --git a/x.bin b/x.bin\nGIT binary patch\n",
    ],
)
def test_blocks_invalid_sensitive_traversal_modes_and_binary(
    git_repository: Path, patch: str
) -> None:
    before = state(git_repository)
    result = PatchProcessor().process(git_repository, patch)
    assert result.status == "blocked"
    assert not result.policy_allowed
    assert not result.workspace_created
    assert state(git_repository) == before


def test_rejects_dirty_repository(git_repository: Path, valid_patch: str) -> None:
    (git_repository / "calculator.py").write_text("dirty = True\n", encoding="utf-8")
    result = PatchProcessor().process(git_repository, valid_patch)
    assert result.status == "failed"
    assert "clean working tree" in result.errors[0]


def test_rejects_tracked_symlink_mode(scanning_repository: Path, valid_patch: str) -> None:
    result = PatchProcessor().process(scanning_repository, valid_patch)
    assert result.status == "failed"
    assert "symlink" in result.errors[0]


def test_enforces_workspace_and_patch_limits(git_repository: Path, valid_patch: str) -> None:
    small_workspace = Settings(workspace=WorkspaceLimits(max_total_bytes=10))
    result = PatchProcessor(small_workspace).process(git_repository, valid_patch)
    assert result.status == "failed"
    assert "byte limit" in result.errors[0]

    one_line = Settings(patch=PatchLimits(max_changed_lines=1))
    result = PatchProcessor(one_line).process(git_repository, valid_patch)
    assert result.status == "blocked"
    assert "changed lines" in result.errors[0]

    one_file = Settings(patch=PatchLimits(max_files=1))
    multi_file = valid_patch + (
        "diff --git a/helper.py b/helper.py\n"
        "--- a/helper.py\n+++ b/helper.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n"
    )
    result = PatchProcessor(one_file).process(git_repository, multi_file)
    assert result.status == "blocked"
    assert "files" in result.errors[0]


def test_revalidates_modified_patch_after_preparation(
    git_repository: Path, valid_patch: str
) -> None:
    processor = PatchProcessor()
    prepared = processor.prepare(git_repository, valid_patch)
    try:
        result = processor.apply_prepared(prepared, valid_patch + "\n")
        assert result.status == "blocked"
        assert "patch content changed" in result.errors[0]
    finally:
        assert prepared.workspace is not None
        assert processor.manager.cleanup(prepared.workspace)[0]


def test_revalidates_source_after_preparation(git_repository: Path, valid_patch: str) -> None:
    processor = PatchProcessor()
    prepared = processor.prepare(git_repository, valid_patch)
    try:
        (git_repository / "calculator.py").write_text("changed = True\n", encoding="utf-8")
        result = processor.apply_prepared(prepared, valid_patch)
        assert result.status == "blocked"
        assert not result.original_unchanged
    finally:
        assert prepared.workspace is not None
        assert processor.manager.cleanup(prepared.workspace)[0]


def test_patch_conflict_fails_and_cleans(git_repository: Path, valid_patch: str) -> None:
    conflict = valid_patch.replace("return dividend / divisor", "return missing / context")
    result = PatchProcessor().process(git_repository, conflict)
    assert result.status == "failed"
    assert not result.applicable
    assert result.workspace_cleaned


def test_apply_failure_is_reported_and_cleaned(
    git_repository: Path, valid_patch: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_git = processor_module._git

    def fail_apply(root: Path, *arguments: str, input_bytes: bytes | None = None):
        if arguments[:1] == ("apply",) and "--check" not in arguments:
            return subprocess.CompletedProcess(arguments, 1, b"", b"simulated")
        return real_git(root, *arguments, input_bytes=input_bytes)

    monkeypatch.setattr(processor_module, "_git", fail_apply)
    result = PatchProcessor().process(git_repository, valid_patch)
    assert result.status == "failed"
    assert result.applicable is False
    assert result.workspace_cleaned


def test_interrupt_is_reported_and_cleaned(
    git_repository: Path, valid_patch: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(PatchProcessor, "apply_prepared", interrupt)
    result = PatchProcessor().process(git_repository, valid_patch)
    assert result.status == "interrupted"
    assert result.workspace_created and result.workspace_cleaned


def test_unexpected_workspace_change_fails_closed(
    git_repository: Path, valid_patch: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_git = processor_module._git

    def mutate_after_apply(root: Path, *arguments: str, input_bytes: bytes | None = None):
        completed = real_git(root, *arguments, input_bytes=input_bytes)
        if arguments[:1] == ("apply",) and "--check" not in arguments:
            (root / "unexpected.py").write_bytes(b"surprise = True\n")
        return completed

    monkeypatch.setattr(processor_module, "_git", mutate_after_apply)
    result = PatchProcessor().process(git_repository, valid_patch)
    assert result.status == "failed"
    assert "declared patch targets" in result.errors[0]
    assert result.workspace_cleaned


def test_cleanup_error_is_reported(git_repository: Path, valid_patch: str) -> None:
    retained: list[Path] = []

    def fail_cleanup(path: Path) -> None:
        retained.append(path)
        raise OSError("simulated cleanup failure")

    manager = WorkspaceManager(remover=fail_cleanup)
    result = PatchProcessor(manager=manager).process(git_repository, valid_patch)
    assert result.status == "applied"
    assert not result.workspace_cleaned
    assert result.cleanup_error == "simulated cleanup failure"
    assert result.workspace_created
    # Use the real remover to avoid leaking the intentionally retained test workspace.
    WorkspaceManager().cleanup_path(retained[0])


def test_repeated_operations_preserve_repository(git_repository: Path, valid_patch: str) -> None:
    before = state(git_repository)
    assert PatchProcessor().process(git_repository, valid_patch).status == "applied"
    assert PatchProcessor().process(git_repository, valid_patch).status == "applied"
    assert state(git_repository) == before


def test_unicode_filename_patch(tmp_path: Path) -> None:
    repository = tmp_path / "unicode"
    repository.mkdir()
    target = repository / "café.py"
    target.write_bytes(b"value = 1\n")
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=LACE",
            "-c",
            "user.email=lace@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "baseline",
        ],
        check=True,
    )
    patch = """diff --git a/café.py b/café.py
--- a/café.py
+++ b/café.py
@@ -1 +1 @@
-value = 1
+value = 2
"""
    result = PatchProcessor().process(repository, patch)
    assert result.status == "applied", result
    assert result.changed_files == ("café.py",)
    assert target.read_text(encoding="utf-8") == "value = 1\n"
