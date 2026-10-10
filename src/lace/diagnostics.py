"""Environment diagnostics shared by command and interactive interfaces."""

import platform
import shutil
import subprocess
import sys
from typing import Any

from lace.config import ExecutionPolicy
from lace.execution.docker import DockerExecutor


def _tool_version(command: str, arguments: list[str]) -> tuple[str, str]:
    executable = shutil.which(command)
    if executable is None:
        return "unavailable", "not found on PATH"
    try:
        completed = subprocess.run(
            [executable, *arguments], capture_output=True, text=True, check=False, timeout=3
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return "unavailable", str(error)
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return (
        "ready" if completed.returncode == 0 else "unavailable",
        output[0] if output else "unknown",
    )


def collect_diagnostics(version: str) -> dict[str, Any]:
    """Return capability facts without claiming future integrations are verified."""
    git_status, git_version = _tool_version("git", ["--version"])
    ollama_status, ollama_version = _tool_version("ollama", ["--version"])
    container = "podman" if shutil.which("podman") else "docker" if shutil.which("docker") else None
    container_status, container_version = (
        _tool_version(container, ["--version"])
        if container
        else ("unavailable", "not found on PATH")
    )
    foundation_ready = git_status == "ready" and sys.version_info >= (3, 12)
    isolation_check, isolation_meta = DockerExecutor().verify(ExecutionPolicy())
    return {
        "lace": version,
        "python": {"status": "ready", "version": platform.python_version()},
        "git": {"status": git_status, "version": git_version},
        "ollama": {"status": ollama_status, "version": ollama_version, "required_from": "M5"},
        "isolation": {
            "status": container_status,
            "runtime": container,
            "version": container_version,
            "required_from": "M4",
            "verified": isolation_check.verified,
            "image": isolation_meta.image,
            "image_id": isolation_meta.image_id,
            "errors": list(isolation_check.errors),
        },
        "m1_ready": foundation_ready,
        "m2_ready": foundation_ready,
        "m4_ready": foundation_ready and isolation_check.verified,
    }
