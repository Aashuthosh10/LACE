"""Validated Milestone 1 settings."""

from pydantic import BaseModel, ConfigDict, Field


class PatchLimits(BaseModel):
    """Hard resource bounds applied before Git sees a patch."""

    model_config = ConfigDict(frozen=True)

    max_bytes: int = Field(default=1_048_576, ge=1, le=10_485_760)
    max_files: int = Field(default=20, ge=1, le=1_000)
    max_changed_lines: int = Field(default=2_000, ge=1, le=100_000)


class RepositoryLimits(BaseModel):
    """Bounds for repository inventory and selected source context."""

    model_config = ConfigDict(frozen=True)

    max_files: int = Field(default=10_000, ge=1, le=100_000)
    max_total_bytes: int = Field(default=52_428_800, ge=1, le=1_073_741_824)
    max_file_bytes: int = Field(default=262_144, ge=1, le=10_485_760)
    max_context_chars: int = Field(default=50_000, ge=1, le=2_000_000)
    max_selected_files: int = Field(default=20, ge=1, le=1_000)


class WorkspaceLimits(BaseModel):
    """Hard limits for disposable tracked-file workspaces."""

    model_config = ConfigDict(frozen=True)

    max_files: int = Field(default=10_000, ge=1, le=100_000)
    max_total_bytes: int = Field(default=52_428_800, ge=1, le=1_073_741_824)
    max_file_bytes: int = Field(default=10_485_760, ge=1, le=104_857_600)


class ExecutionPolicy(BaseModel):
    """Administrator-controlled restricted pytest policy."""

    model_config = ConfigDict(frozen=True)
    runtime: str = "docker"
    image: str = "lace-pytest:3.12-v1"
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    output_bytes: int = Field(default=2_097_152, ge=1024, le=20_971_520)
    cpus: float = Field(default=2.0, gt=0, le=16)
    memory: str = "2g"
    pids: int = Field(default=256, ge=16, le=4096)


class Settings(BaseModel):
    """Application settings with explicit, immutable defaults."""

    model_config = ConfigDict(frozen=True)

    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    patch: PatchLimits = Field(default_factory=PatchLimits)
    repository: RepositoryLimits = Field(default_factory=RepositoryLimits)
    workspace: WorkspaceLimits = Field(default_factory=WorkspaceLimits)
    execution: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
