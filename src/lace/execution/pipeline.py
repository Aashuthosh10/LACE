"""M3 patch preparation followed by restricted tests and unconditional cleanup."""

import dataclasses
from pathlib import Path

from lace.config import Settings
from lace.execution.docker import DockerExecutor
from lace.execution.models import ExecutionRequest, PipelineResult
from lace.workspace import PatchProcessor


class RestrictedTestPipeline:
    def __init__(
        self, settings: Settings | None = None, executor: DockerExecutor | None = None
    ) -> None:
        self.settings = settings or Settings()
        self.processor = PatchProcessor(self.settings)
        self.executor = executor or DockerExecutor()

    def run(self, repository: Path, patch_text: str) -> PipelineResult:
        prepared = self.processor.prepare(repository, patch_text)
        workspace_result = self.processor.apply_prepared(prepared, patch_text)
        test_result = None
        try:
            if workspace_result.applied and prepared.workspace is not None:
                test_result = self.executor.execute(
                    ExecutionRequest(prepared.workspace.path, self.settings.execution)
                )
        finally:
            if prepared.workspace is not None:
                cleaned, error = self.processor.manager.cleanup(prepared.workspace)
                workspace_result = dataclasses.replace(
                    workspace_result, workspace_cleaned=cleaned, cleanup_error=error
                )
        return PipelineResult(workspace_result, test_result)
