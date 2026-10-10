"""Controlled patch preparation and application in disposable workspaces."""

import dataclasses
import hashlib
from pathlib import Path

from lace.config import Settings
from lace.patches import assess_patch
from lace.risk import score_patch
from lace.workspace.manager import WorkspaceManager, _git
from lace.workspace.models import (
    PreparedPatch,
    WorkspaceApplyResult,
    WorkspaceError,
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PatchProcessor:
    """Revalidate and apply a patch only inside a disposable workspace."""

    def __init__(
        self, settings: Settings | None = None, manager: WorkspaceManager | None = None
    ) -> None:
        self.settings = settings or Settings()
        self.manager = manager or WorkspaceManager(self.settings.workspace)

    def prepare(self, repository: Path, patch_text: str) -> PreparedPatch:
        assessment = assess_patch(patch_text, self.settings)
        risk = score_patch(assessment, patch_text)
        workspace = self.manager.create(repository) if assessment.policy_allowed else None
        return PreparedPatch(assessment, risk, workspace)

    def apply_prepared(self, prepared: PreparedPatch, patch_text: str) -> WorkspaceApplyResult:
        assessment = assess_patch(patch_text, self.settings)
        base = dict(
            patch_sha256=assessment.sha256,
            policy_allowed=assessment.policy_allowed,
            risk=score_patch(assessment, patch_text),
            applicable=False,
            applied=False,
            changed_files=(),
            original_unchanged=True,
            workspace_created=prepared.workspace is not None,
            workspace_cleaned=False,
            cleanup_error=None,
        )
        if assessment.sha256 != prepared.assessment.sha256:
            return WorkspaceApplyResult(
                status="blocked", errors=("patch content changed after preparation",), **base
            )
        if not assessment.policy_allowed or assessment.patch is None:
            return WorkspaceApplyResult(status="blocked", errors=assessment.errors, **base)
        if prepared.workspace is None:
            return WorkspaceApplyResult(
                status="failed", errors=("workspace is unavailable",), **base
            )
        handle = prepared.workspace
        original_unchanged = self.manager.matches_original(handle.snapshot)
        if not original_unchanged:
            return WorkspaceApplyResult(
                status="blocked",
                errors=("original repository changed after preparation",),
                **{**base, "original_unchanged": False},
            )
        if self.manager.workspace_files(handle.path) != handle.snapshot.files:
            return WorkspaceApplyResult(
                status="blocked", errors=("workspace baseline changed before application",), **base
            )

        payload = patch_text.encode("utf-8")
        checked = _git(
            handle.path,
            "apply",
            "--check",
            "--recount",
            "--whitespace=error",
            "-",
            input_bytes=payload,
        )
        if checked.returncode != 0:
            detail = checked.stderr.decode("utf-8", errors="replace").strip().splitlines()
            error = detail[0] if detail else "unknown Git applicability error"
            return WorkspaceApplyResult(
                status="failed", errors=(f"Git rejected patch applicability: {error}",), **base
            )
        applied = _git(
            handle.path, "apply", "--recount", "--whitespace=error", "-", input_bytes=payload
        )
        if applied.returncode != 0:
            return WorkspaceApplyResult(
                status="failed", errors=("Git failed while applying the checked patch",), **base
            )

        after = self.manager.workspace_files(handle.path)
        before_map = {item.path: (item.sha256, item.mode) for item in handle.snapshot.files}
        after_map = {item.path: (item.sha256, item.mode) for item in after}
        changed = tuple(
            sorted(
                path
                for path in before_map.keys() | after_map.keys()
                if before_map.get(path) != after_map.get(path)
            )
        )
        expected = tuple(sorted(assessment.patch.targets))
        if changed != expected:
            return WorkspaceApplyResult(
                status="failed",
                errors=("post-application changes do not match declared patch targets",),
                **{**base, "applicable": True, "changed_files": changed},
            )
        original_unchanged = self.manager.matches_original(handle.snapshot)
        if not original_unchanged:
            return WorkspaceApplyResult(
                status="failed",
                errors=("original repository changed during workspace processing",),
                **{
                    **base,
                    "applicable": True,
                    "changed_files": changed,
                    "original_unchanged": False,
                },
            )
        return WorkspaceApplyResult(
            status="applied",
            errors=(),
            **{**base, "applicable": True, "applied": True, "changed_files": changed},
        )

    def process(self, repository: Path, patch_text: str) -> WorkspaceApplyResult:
        prepared: PreparedPatch | None = None
        result: WorkspaceApplyResult | None = None
        try:
            prepared = self.prepare(repository, patch_text)
            result = self.apply_prepared(prepared, patch_text)
        except KeyboardInterrupt:
            assessment = assess_patch(patch_text, self.settings)
            result = WorkspaceApplyResult(
                "interrupted",
                assessment.sha256,
                assessment.policy_allowed,
                score_patch(assessment, patch_text),
                False,
                False,
                (),
                ("operation interrupted",),
                True,
                prepared is not None and prepared.workspace is not None,
                False,
            )
        except (OSError, WorkspaceError) as error:
            assessment = assess_patch(patch_text, self.settings)
            result = WorkspaceApplyResult(
                "blocked" if not assessment.policy_allowed else "failed",
                assessment.sha256,
                assessment.policy_allowed,
                score_patch(assessment, patch_text),
                False,
                False,
                (),
                (str(error),),
                True,
                prepared is not None and prepared.workspace is not None,
                False,
            )
        finally:
            if prepared is not None and prepared.workspace is not None:
                cleaned, cleanup_error = self.manager.cleanup(prepared.workspace)
                if result is not None:
                    result = dataclasses.replace(
                        result, workspace_cleaned=cleaned, cleanup_error=cleanup_error
                    )
        if result is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("workspace processing ended without a result")
        return result
