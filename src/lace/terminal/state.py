"""Ephemeral interactive-session state."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

DetailKind = Literal["scan", "validation", "workspace", "test"]


@dataclass(frozen=True)
class ActivityDetails:
    kind: DetailKind
    title: str
    payload: dict[str, Any]


@dataclass
class SessionState:
    repository: Path | None = None
    phase: Literal["ready", "running", "stopped"] = "ready"
    last_activity: ActivityDetails | None = None
