"""Creation, verification, and cleanup of tracked-file disposable workspaces."""

import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path, PurePosixPath

from lace.config import WorkspaceLimits
from lace.repository import contained_regular_file, exclusion_reason, tracked_entries
from lace.workspace.models import FileSnapshot, RepositorySnapshot, WorkspaceError, WorkspaceHandle


def _git(
    root: Path, *arguments: str, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        input=input_bytes,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _git_value(root: Path, *arguments: str) -> str:
    completed = _git(root, *arguments)
    if completed.returncode != 0:
        raise WorkspaceError(f"Git command failed: {' '.join(arguments)}")
    return os.fsdecode(completed.stdout).strip()


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _remove_tree(path: Path) -> None:
    def make_writable(function, target, _error) -> None:  # type: ignore[no-untyped-def]
        os.chmod(target, stat.S_IWRITE)
        function(target)

    shutil.rmtree(path, onexc=make_writable)


class WorkspaceManager:
    """Manage exact, non-executable copies of supported tracked repository files."""

    def __init__(
        self,
        limits: WorkspaceLimits | None = None,
        *,
        temporary_parent: Path | None = None,
        remover: Callable[[Path], None] | None = None,
    ) -> None:
        self.limits = limits or WorkspaceLimits()
        self.temporary_parent = temporary_parent
        self._remover = remover or _remove_tree

    def snapshot(self, repository: Path) -> RepositorySnapshot:
        requested = repository.resolve()
        root_text = _git_value(requested, "rev-parse", "--show-toplevel")
        root = Path(root_text).resolve()
        if root != requested:
            raise WorkspaceError("repository path must be the Git work-tree root")
        status_result = _git(root, "status", "--porcelain=v1", "--untracked-files=all", "-z")
        if status_result.returncode != 0:
            raise WorkspaceError("Git could not inspect repository status")
        if status_result.stdout:
            raise WorkspaceError("repository must have a clean working tree for M3")

        entries = tracked_entries(root)
        if len(entries) > self.limits.max_files:
            raise WorkspaceError(f"repository exceeds {self.limits.max_files} tracked files")
        files: list[FileSnapshot] = []
        excluded: list[str] = []
        total = 0
        for mode, relative in entries:
            if mode in {"120000", "160000"}:
                label = "symlink" if mode == "120000" else "submodule"
                raise WorkspaceError(f"tracked {label} is unsupported: {relative}")
            if mode not in {"100644", "100755"}:
                raise WorkspaceError(f"unsupported Git mode {mode}: {relative}")
            if exclusion_reason(relative):
                excluded.append(relative)
                continue
            source, reason = contained_regular_file(root, relative)
            if reason or source is None:
                raise WorkspaceError(f"unsafe tracked path {relative}: {reason or 'unknown'}")
            size = source.stat().st_size
            if size > self.limits.max_file_bytes:
                raise WorkspaceError(f"tracked file exceeds size limit: {relative}")
            total += size
            if total > self.limits.max_total_bytes:
                raise WorkspaceError("repository exceeds workspace byte limit")
            data = source.read_bytes()
            files.append(FileSnapshot(relative, _hash(data), len(data), mode))
        return RepositorySnapshot(
            root=root,
            head_commit=_git_value(root, "rev-parse", "HEAD"),
            tree_hash=_git_value(root, "rev-parse", "HEAD^{tree}"),
            files=tuple(files),
            excluded=tuple(excluded),
        )

    def matches_original(self, snapshot: RepositorySnapshot) -> bool:
        try:
            current = self.snapshot(snapshot.root)
        except (OSError, WorkspaceError):
            return False
        return current == snapshot

    def create(self, repository: Path) -> WorkspaceHandle:
        snapshot = self.snapshot(repository)
        parent = self.temporary_parent.resolve() if self.temporary_parent else None
        workspace = Path(tempfile.mkdtemp(prefix="lace-workspace-", dir=parent)).resolve()
        try:
            workspace.relative_to(snapshot.root)
        except ValueError:
            pass
        else:
            self.cleanup_path(workspace)
            raise WorkspaceError("temporary workspace must be outside the original repository")

        try:
            for file in snapshot.files:
                source, reason = contained_regular_file(snapshot.root, file.path)
                if reason or source is None:
                    raise WorkspaceError(f"source changed before copy: {file.path}")
                data = source.read_bytes()
                if len(data) != file.size_bytes or _hash(data) != file.sha256:
                    raise WorkspaceError(f"source changed before copy: {file.path}")
                target = workspace.joinpath(*PurePosixPath(file.path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                if file.mode == "100755":
                    target.chmod(target.stat().st_mode | stat.S_IXUSR)
            if not self.matches_original(snapshot):
                raise WorkspaceError("original repository changed during workspace creation")
            initialized = _git(workspace, "init", "--quiet")
            if initialized.returncode != 0:
                raise WorkspaceError("could not initialize disposable workspace Git metadata")
            _git(workspace, "config", "core.autocrlf", "false")
            _git(workspace, "add", "--all")
            if self.workspace_files(workspace) != snapshot.files:
                raise WorkspaceError("workspace copy does not match the repository snapshot")
            return WorkspaceHandle(workspace, snapshot)
        except BaseException:
            with suppress(OSError):
                self.cleanup_path(workspace)
            raise

    def workspace_files(self, workspace: Path) -> tuple[FileSnapshot, ...]:
        files: list[FileSnapshot] = []
        total = 0
        for current_root, directories, names in os.walk(workspace, topdown=True, followlinks=False):
            directories[:] = sorted(name for name in directories if name != ".git")
            base = Path(current_root)
            for directory in directories:
                if (base / directory).is_symlink():
                    raise WorkspaceError("workspace contains a symlink directory")
            for name in sorted(names):
                path = base / name
                if path.is_symlink():
                    raise WorkspaceError("workspace contains a symlink file")
                relative = path.relative_to(workspace).as_posix()
                if exclusion_reason(relative):
                    raise WorkspaceError(f"workspace contains forbidden path: {relative}")
                data = path.read_bytes()
                total += len(data)
                if len(files) + 1 > self.limits.max_files or total > self.limits.max_total_bytes:
                    raise WorkspaceError("post-application workspace exceeds configured limits")
                if len(data) > self.limits.max_file_bytes:
                    raise WorkspaceError(f"post-application file exceeds limit: {relative}")
                executable = bool(path.stat().st_mode & stat.S_IXUSR)
                files.append(
                    FileSnapshot(
                        relative, _hash(data), len(data), "100755" if executable else "100644"
                    )
                )
        return tuple(sorted(files, key=lambda item: item.path.casefold()))

    def cleanup(self, handle: WorkspaceHandle) -> tuple[bool, str | None]:
        try:
            self.cleanup_path(handle.path)
        except Exception as error:  # cleanup failures must be reported, never hidden
            return False, str(error)
        return (
            not handle.path.exists(),
            None if not handle.path.exists() else "workspace still exists",
        )

    def cleanup_path(self, path: Path) -> None:
        resolved = path.resolve()
        if not resolved.name.startswith("lace-workspace-"):
            raise WorkspaceError("refusing to clean an unrecognized workspace path")
        self._remover(resolved)
