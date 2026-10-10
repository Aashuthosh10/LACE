"""Read-only, bounded inventory of Git-tracked repository files."""

import hashlib
import os
import subprocess
from pathlib import Path, PurePosixPath

from lace.config import RepositoryLimits
from lace.patches.policy import validate_target_path
from lace.repository.models import (
    Exclusion,
    FileKind,
    FileMetadata,
    RepositoryInventory,
    RepositoryScanError,
)

_VIRTUAL_DIRS = {".venv", "venv", "env", ".tox", ".nox"}
_CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".cache"}
_GENERATED_DIRS = {"build", "dist", "htmlcov", "node_modules", "site-packages"}
_GENERATED_SUFFIXES = {".pyc", ".pyo", ".so", ".dll", ".dylib", ".class"}
_DEPENDENCY_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
}
_CONFIG_NAMES = {"tox.ini", "pytest.ini", "setup.cfg", "ruff.toml", ".pre-commit-config.yaml"}


def _git_root(repository: Path) -> Path:
    requested = repository.resolve()
    completed = subprocess.run(
        ["git", "-C", str(requested), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RepositoryScanError("repository must be inside a Git work tree")
    output = os.fsdecode(completed.stdout).strip()
    root = Path(output).resolve()
    if root != requested:
        raise RepositoryScanError("repository path must be the Git work-tree root")
    return root


def _tracked_entries(root: Path) -> list[tuple[str, str]]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "-z"],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RepositoryScanError("Git could not enumerate tracked files")
    entries: list[tuple[str, str]] = []
    for record in completed.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode = metadata.split(b" ", 1)[0].decode("ascii")
            path = os.fsdecode(raw_path)
        except (ValueError, UnicodeError) as error:
            raise RepositoryScanError("Git returned an invalid tracked-file record") from error
        entries.append((mode, path))
    return sorted(entries, key=lambda entry: entry[1].casefold())


def _excluded_by_path(path: str) -> str | None:
    policy_errors = validate_target_path(path)
    if policy_errors:
        return "sensitive_or_unsafe_path"
    parts = tuple(part.casefold() for part in PurePosixPath(path).parts)
    if any(part in _VIRTUAL_DIRS for part in parts):
        return "virtual_environment"
    if any(part in _CACHE_DIRS for part in parts):
        return "cache"
    if any(part in _GENERATED_DIRS for part in parts):
        return "generated"
    if PurePosixPath(path).suffix.casefold() in _GENERATED_SUFFIXES:
        return "generated"
    return None


def _kind(path: str) -> FileKind:
    pure = PurePosixPath(path)
    name = pure.name.casefold()
    parts = tuple(part.casefold() for part in pure.parts)
    if pure.suffix.casefold() == ".py":
        if (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "tests" in parts
            or "test" in parts
        ):
            return "test"
        return "python"
    if name in _DEPENDENCY_NAMES:
        return "dependency"
    if name in _CONFIG_NAMES or pure.suffix.casefold() in {
        ".toml",
        ".ini",
        ".cfg",
        ".yaml",
        ".yml",
    }:
        return "configuration"
    if pure.suffix.casefold() in {".md", ".rst", ".txt"}:
        return "documentation"
    return "other"


def _contained_regular_file(root: Path, relative: str) -> tuple[Path | None, str | None]:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            return None, "symlink"
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None, "outside_repository_or_missing"
    if not resolved.is_file():
        return None, "not_regular_file"
    return resolved, None


def scan_repository(root: Path, limits: RepositoryLimits | None = None) -> RepositoryInventory:
    """Inventory safe Git-tracked files without executing repository content."""
    limits = limits or RepositoryLimits()
    repository = _git_root(root)
    entries = _tracked_entries(repository)
    if len(entries) > limits.max_files:
        raise RepositoryScanError(f"repository exceeds the {limits.max_files}-file inventory limit")

    files: list[FileMetadata] = []
    exclusions: list[Exclusion] = []
    total_bytes = 0
    warnings: list[str] = []
    for mode, relative in entries:
        reason = _excluded_by_path(relative)
        if reason:
            exclusions.append(Exclusion(relative, reason))
            continue
        if mode == "120000":
            exclusions.append(Exclusion(relative, "symlink"))
            continue
        if mode not in {"100644", "100755"}:
            exclusions.append(Exclusion(relative, "unsupported_git_mode"))
            continue
        file_path, reason = _contained_regular_file(repository, relative)
        if reason or file_path is None:
            exclusions.append(Exclusion(relative, reason or "unsafe_file"))
            continue
        size = file_path.stat().st_size
        total_bytes += size
        if total_bytes > limits.max_total_bytes:
            raise RepositoryScanError(
                f"tracked content exceeds the {limits.max_total_bytes}-byte inventory limit"
            )
        if size > limits.max_file_bytes:
            exclusions.append(Exclusion(relative, "file_too_large"))
            continue
        data = file_path.read_bytes()
        if b"\0" in data[:8192]:
            exclusions.append(Exclusion(relative, "binary"))
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            exclusions.append(Exclusion(relative, "non_utf8"))
            continue
        files.append(
            FileMetadata(
                path=relative,
                kind=_kind(relative),
                size_bytes=size,
                line_count=len(text.splitlines()),
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )

    if not entries:
        warnings.append("repository has no tracked files")
    if entries and not any(file.is_python for file in files):
        warnings.append("repository has no eligible Python source or test files")
    return RepositoryInventory(
        root=repository,
        tracked_count=len(entries),
        files=tuple(files),
        exclusions=tuple(exclusions),
        total_bytes=total_bytes,
        warnings=tuple(warnings),
    )


def read_inventory_text(root: Path, metadata: FileMetadata) -> str:
    """Revalidate and read a previously inventoried file without following links."""
    file_path, reason = _contained_regular_file(root, metadata.path)
    if reason or file_path is None:
        raise RepositoryScanError(f"tracked file changed or became unsafe: {metadata.path}")
    data = file_path.read_bytes()
    if len(data) != metadata.size_bytes or hashlib.sha256(data).hexdigest() != metadata.sha256:
        raise RepositoryScanError(f"tracked file changed during context selection: {metadata.path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RepositoryScanError(f"tracked file encoding changed: {metadata.path}") from error
