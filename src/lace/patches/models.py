"""Patch validation contracts."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PatchInfo:
    targets: tuple[str, ...]
    additions: int
    deletions: int


@dataclass(frozen=True)
class ValidationResult:
    allowed: bool
    applicable: bool
    patch: PatchInfo | None
    errors: tuple[str, ...]
    repository: Path
    original_unchanged: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["repository"] = str(self.repository)
        return data
