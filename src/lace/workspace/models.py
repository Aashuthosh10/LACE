"""Typed contracts for disposable workspace patch processing."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from lace.patches.assessment import PatchAssessment
from lace.risk import RiskAssessment

WorkspaceStatus = Literal["applied", "blocked", "failed", "interrupted"]


class WorkspaceError(RuntimeError):
    """A fail-closed workspace lifecycle error."""


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    sha256: str
    size_bytes: int
    mode: str


@dataclass(frozen=True)
class RepositorySnapshot:
    root: Path
    head_commit: str
    tree_hash: str
    files: tuple[FileSnapshot, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceHandle:
    path: Path
    snapshot: RepositorySnapshot


@dataclass(frozen=True)
class PreparedPatch:
    assessment: PatchAssessment
    risk: RiskAssessment
    workspace: WorkspaceHandle | None


@dataclass(frozen=True)
class WorkspaceApplyResult:
    status: WorkspaceStatus
    patch_sha256: str
    policy_allowed: bool
    risk: RiskAssessment
    applicable: bool
    applied: bool
    changed_files: tuple[str, ...]
    errors: tuple[str, ...]
    original_unchanged: bool
    workspace_created: bool
    workspace_cleaned: bool
    cleanup_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk"] = self.risk.to_dict()
        return data
