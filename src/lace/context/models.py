"""Relevant-context selection contracts."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SelectedFile:
    path: str
    score: int
    reasons: tuple[str, ...]
    context_chars: int


@dataclass(frozen=True)
class ContextSelection:
    task: str
    files: tuple[SelectedFile, ...]
    context: str
    context_chars: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "selected_files": [asdict(file) for file in self.files],
            "context_chars": self.context_chars,
            "warnings": list(self.warnings),
        }
