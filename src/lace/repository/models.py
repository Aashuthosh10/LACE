"""Typed repository inventory contracts."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

FileKind = Literal["python", "test", "configuration", "dependency", "documentation", "other"]


class RepositoryScanError(ValueError):
    """Raised when a repository cannot be inventoried safely."""


@dataclass(frozen=True)
class FileMetadata:
    path: str
    kind: FileKind
    size_bytes: int
    line_count: int | None
    sha256: str

    @property
    def is_python(self) -> bool:
        return self.kind in {"python", "test"}


@dataclass(frozen=True)
class Exclusion:
    path: str
    reason: str


@dataclass(frozen=True)
class RepositoryInventory:
    root: Path
    tracked_count: int
    files: tuple[FileMetadata, ...]
    exclusions: tuple[Exclusion, ...]
    total_bytes: int
    warnings: tuple[str, ...]

    @property
    def python_files(self) -> tuple[FileMetadata, ...]:
        return tuple(file for file in self.files if file.is_python)

    @property
    def exclusion_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for exclusion in self.exclusions:
            counts[exclusion.reason] = counts.get(exclusion.reason, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "tracked_count": self.tracked_count,
            "files_scanned": len(self.files),
            "python_files": len(self.python_files),
            "total_bytes": self.total_bytes,
            "files": [asdict(file) for file in self.files],
            "excluded": self.exclusion_counts,
            "warnings": list(self.warnings),
        }
