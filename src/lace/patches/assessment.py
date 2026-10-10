"""Reusable deterministic patch assessment before repository operations."""

import hashlib
from dataclasses import dataclass

from lace.config import Settings
from lace.patches.models import PatchInfo
from lace.patches.parser import PatchParseError, parse_unified_diff
from lace.patches.policy import validate_target_path


@dataclass(frozen=True)
class PatchAssessment:
    sha256: str
    policy_allowed: bool
    patch: PatchInfo | None
    errors: tuple[str, ...]


def assess_patch(patch_text: str, settings: Settings | None = None) -> PatchAssessment:
    """Parse, bound, and path-check a patch without touching a repository."""
    settings = settings or Settings()
    digest = hashlib.sha256(patch_text.encode("utf-8")).hexdigest()
    try:
        info = parse_unified_diff(
            patch_text,
            max_bytes=settings.patch.max_bytes,
            max_files=settings.patch.max_files,
            max_changed_lines=settings.patch.max_changed_lines,
        )
    except (PatchParseError, UnicodeError) as error:
        return PatchAssessment(digest, False, None, (str(error),))
    errors = tuple(error for target in info.targets for error in validate_target_path(target))
    return PatchAssessment(digest, not errors, info, errors)
