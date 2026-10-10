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


class Settings(BaseModel):
    """Application settings with explicit, immutable defaults."""

    model_config = ConfigDict(frozen=True)

    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    patch: PatchLimits = Field(default_factory=PatchLimits)
    repository: RepositoryLimits = Field(default_factory=RepositoryLimits)
