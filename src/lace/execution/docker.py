"""Fail-closed Docker adapter using one fixed pytest command template."""

import json
import re
import shutil
import subprocess
import time
import uuid

from lace.config import ExecutionPolicy
from lace.execution.models import ExecutionRequest, IsolationStatus, RuntimeMetadata, TestResult

_PASSED = re.compile(r"(\d+) passed")
_FAILED = re.compile(r"(\d+) failed")
_CONTROLS = (
    "non-root",
    "network-none",
    "read-only-root",
    "cap-drop-all",
    "no-new-privileges",
    "cpu-limit",
    "memory-limit",
    "pid-limit",
    "bounded-output",
    "timeout",
)


class DockerExecutor:
    def __init__(self, runner=subprocess.run) -> None:
        self._run = runner

    def _metadata(self, policy: ExecutionPolicy, name: str | None = None) -> RuntimeMetadata:
        return RuntimeMetadata(policy.runtime, None, policy.image, None, name)

    def verify(self, policy: ExecutionPolicy) -> tuple[IsolationStatus, RuntimeMetadata]:
        executable = shutil.which(policy.runtime)
        meta = self._metadata(policy)
        if executable is None:
            return IsolationStatus(False, (), ("Docker runtime not found",)), meta
        try:
            info = self._run(
                [executable, "info", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            image = self._run(
                [executable, "image", "inspect", policy.image, "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return IsolationStatus(False, (), (str(error),)), meta
        if info.returncode != 0:
            return IsolationStatus(False, (), ("Docker Linux engine is unavailable",)), meta
        try:
            facts = json.loads(info.stdout)
            image_facts = json.loads(image.stdout) if image.returncode == 0 else {}
        except json.JSONDecodeError:
            return IsolationStatus(
                False, (), ("Docker returned invalid capability metadata",)
            ), meta
        if facts.get("OSType") != "linux":
            return IsolationStatus(False, (), ("Docker Linux containers are required",)), meta
        security = " ".join(facts.get("SecurityOptions") or [])
        if "seccomp" not in security:
            return IsolationStatus(False, (), ("Docker seccomp is unavailable",)), meta
        if image.returncode != 0:
            return IsolationStatus(
                False, (), (f"approved image is not installed: {policy.image}",)
            ), meta
        labels = (image_facts.get("Config") or {}).get("Labels") or {}
        expected = {
            "org.lace.pytest-image": "3.12-v1",
            "org.lace.python-version": "3.12.12",
            "org.lace.pytest-version": "9.0.2",
        }
        errors = tuple(
            f"approved image label mismatch: {key}"
            for key, value in expected.items()
            if labels.get(key) != value
        )
        if image_facts.get("Os") != "linux" or image_facts.get("Architecture") != "amd64":
            errors += ("approved image must be linux/amd64",)
        if (image_facts.get("Config") or {}).get("User") not in {"65534:65534", "65534"}:
            errors += ("approved image default user must be non-root 65534",)
        if errors:
            return IsolationStatus(False, (), errors), meta
        meta = RuntimeMetadata(
            policy.runtime, facts.get("ServerVersion"), policy.image, image_facts.get("Id"), None
        )
        return IsolationStatus(True, _CONTROLS, ()), meta

    def execute(self, request: ExecutionRequest) -> TestResult:
        started = time.monotonic()
        isolation, meta = self.verify(request.policy)
        if not isolation.verified:
            return TestResult(
                "environment_error",
                None,
                "",
                "",
                False,
                time.monotonic() - started,
                None,
                None,
                isolation.errors,
                meta,
                isolation,
                True,
            )
        name = f"lace-test-{uuid.uuid4().hex}"
        meta = RuntimeMetadata(meta.runtime, meta.version, meta.image, meta.image_id, name)
        executable = shutil.which(request.policy.runtime) or request.policy.runtime
        command = [
            executable,
            "run",
            "--name",
            name,
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(request.policy.pids),
            "--memory",
            request.policy.memory,
            "--cpus",
            str(request.policy.cpus),
            "--user",
            "65534:65534",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "--mount",
            f"type=bind,src={request.workspace},dst=/workspace",
            "--workdir",
            "/workspace",
            request.policy.image,
            "python",
            "-m",
            "pytest",
            "-q",
            "--disable-warnings",
            "--maxfail=20",
        ]
        try:
            completed = self._run(
                command, capture_output=True, timeout=request.policy.timeout_seconds, check=False
            )
            raw_out, raw_err = completed.stdout or b"", completed.stderr or b""
            limit = request.policy.output_bytes
            truncated = len(raw_out) + len(raw_err) > limit
            bounded_out = raw_out[:limit]
            bounded_err = raw_err[: max(0, limit - len(bounded_out))]
            joined = bounded_out + bounded_err
            text = joined.decode("utf-8", errors="replace")
            passed_matches = _PASSED.findall(text)
            failed_matches = _FAILED.findall(text)
            passed = int(passed_matches[-1]) if passed_matches else 0
            failed = int(failed_matches[-1]) if failed_matches else 0
            status = (
                "passed"
                if completed.returncode == 0
                else "failed"
                if completed.returncode == 1
                else "infrastructure_error"
            )
            return TestResult(
                status,
                completed.returncode,
                bounded_out.decode("utf-8", "replace"),
                bounded_err.decode("utf-8", "replace"),
                truncated,
                time.monotonic() - started,
                passed,
                failed,
                tuple(line for line in text.splitlines() if line.startswith("FAILED "))[:20],
                meta,
                isolation,
                True,
            )
        except subprocess.TimeoutExpired:
            self._run([executable, "rm", "-f", name], capture_output=True, check=False, timeout=10)
            return TestResult(
                "timeout",
                None,
                "",
                "",
                False,
                time.monotonic() - started,
                None,
                None,
                (f"execution exceeded {request.policy.timeout_seconds} seconds",),
                meta,
                isolation,
                True,
            )
        except KeyboardInterrupt:
            self._run([executable, "rm", "-f", name], capture_output=True, check=False, timeout=10)
            return TestResult(
                "interrupted",
                None,
                "",
                "",
                False,
                time.monotonic() - started,
                None,
                None,
                ("execution interrupted",),
                meta,
                isolation,
                True,
            )
        except OSError as error:
            return TestResult(
                "infrastructure_error",
                None,
                "",
                "",
                False,
                time.monotonic() - started,
                None,
                None,
                (str(error),),
                meta,
                isolation,
                False,
                str(error),
            )
