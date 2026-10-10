import json
import subprocess
from pathlib import Path

from lace.config import ExecutionPolicy
from lace.execution import DockerExecutor, ExecutionRequest


class FakeRunner:
    def __init__(self, test_code: int = 0, timeout: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.test_code = test_code
        self.timeout = timeout

    def __call__(self, command, **_kwargs):
        self.commands.append(command)
        if command[1:2] == ["info"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {"OSType": "linux", "SecurityOptions": ["name=seccomp"], "ServerVersion": "1"}
                ),
                "",
            )
        if command[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "Id": "sha256:test",
                        "Os": "linux",
                        "Architecture": "amd64",
                        "Config": {
                            "User": "65534:65534",
                            "Labels": {
                                "org.lace.pytest-image": "3.12-v1",
                                "org.lace.python-version": "3.12.12",
                                "org.lace.pytest-version": "9.0.2",
                            },
                        },
                    }
                ),
                "",
            )
        if self.timeout and command[1:2] == ["run"]:
            raise subprocess.TimeoutExpired(command, 1)
        output = (
            b"1 passed in 0.01s\n"
            if self.test_code == 0
            else b"FAILED test_x.py::test_x\n1 failed in 0.01s\n"
        )
        return subprocess.CompletedProcess(command, self.test_code, output, b"")


def test_fixed_restricted_command(monkeypatch, tmp_path: Path) -> None:
    fake = FakeRunner()
    monkeypatch.setattr("shutil.which", lambda _name: "docker")
    result = DockerExecutor(fake).execute(ExecutionRequest(tmp_path, ExecutionPolicy()))
    assert result.status == "passed"
    command = fake.commands[-1]
    for expected in ("none", "--read-only", "ALL", "no-new-privileges", "65534:65534"):
        assert expected in command
    assert command[-6:] == ["python", "-m", "pytest", "-q", "--disable-warnings", "--maxfail=20"]


def test_failure_is_not_infrastructure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: "docker")
    result = DockerExecutor(FakeRunner(test_code=1)).execute(
        ExecutionRequest(tmp_path, ExecutionPolicy())
    )
    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.failure_summary == ("FAILED test_x.py::test_x",)


def test_missing_image_fails_closed(monkeypatch, tmp_path: Path) -> None:
    fake = FakeRunner()
    monkeypatch.setattr("shutil.which", lambda _name: None)
    result = DockerExecutor(fake).execute(ExecutionRequest(tmp_path, ExecutionPolicy()))
    assert result.status == "environment_error"
    assert not result.isolation.verified
    assert not fake.commands


def test_timeout_forces_cleanup(monkeypatch, tmp_path: Path) -> None:
    fake = FakeRunner(timeout=True)
    monkeypatch.setattr("shutil.which", lambda _name: "docker")
    result = DockerExecutor(fake).execute(
        ExecutionRequest(tmp_path, ExecutionPolicy(timeout_seconds=1))
    )
    assert result.status == "timeout"
    assert fake.commands[-1][1:3] == ["rm", "-f"]


def test_combined_output_budget(monkeypatch, tmp_path: Path) -> None:
    fake = FakeRunner()
    monkeypatch.setattr("shutil.which", lambda _name: "docker")
    result = DockerExecutor(fake).execute(
        ExecutionRequest(tmp_path, ExecutionPolicy(output_bytes=1024))
    )
    assert len(result.stdout.encode()) + len(result.stderr.encode()) <= 1024
