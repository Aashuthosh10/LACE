"""Typed restricted-test execution contracts."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from lace.config import ExecutionPolicy
from lace.workspace.models import WorkspaceApplyResult

TestStatus = Literal[
    "passed", "failed", "timeout", "environment_error", "infrastructure_error", "interrupted"
]


@dataclass(frozen=True)
class ExecutionRequest:
    workspace: Path
    policy: ExecutionPolicy


@dataclass(frozen=True)
class RuntimeMetadata:
    runtime: str
    version: str | None
    image: str
    image_id: str | None
    container_name: str | None


@dataclass(frozen=True)
class IsolationStatus:
    verified: bool
    controls: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class TestResult:
    status: TestStatus
    exit_code: int | None
    stdout: str
    stderr: str
    output_truncated: bool
    duration_seconds: float
    passed: int | None
    failed: int | None
    failure_summary: tuple[str, ...]
    runtime: RuntimeMetadata
    isolation: IsolationStatus
    cleanup_complete: bool
    cleanup_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PipelineResult:
    workspace: WorkspaceApplyResult
    tests: TestResult | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace.to_dict(),
            "tests": self.tests.to_dict() if self.tests else None,
        }
