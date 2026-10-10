"""Controlled live Docker probes. No fixture in this module runs on host Python."""

import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from lace.config import ExecutionPolicy
from lace.execution import DockerExecutor, ExecutionRequest, RestrictedTestPipeline

pytestmark = pytest.mark.docker_live


def _workspace(tmp_path: Path, source: str) -> Path:
    (tmp_path / "test_probe.py").write_text(source, encoding="utf-8")
    return tmp_path


def _run(workspace: Path, **overrides):
    policy = ExecutionPolicy(**overrides)
    return DockerExecutor().execute(ExecutionRequest(workspace, policy))


def test_live_identity_network_and_filesystem_isolation(tmp_path: Path) -> None:
    workspace = _workspace(
        tmp_path,
        """import os
import pathlib
import socket
import pytest

def test_controls():
    assert os.getuid() == 65534
    assert not pathlib.Path('/host_mnt').exists()
    with pytest.raises(PermissionError):
        pathlib.Path('/root/.ssh').exists()
    with pytest.raises(OSError):
        pathlib.Path('/lace-root-write').write_text('blocked')
    sock = socket.socket()
    sock.settimeout(0.25)
    with pytest.raises(OSError):
        sock.connect(('1.1.1.1', 53))
""",
    )
    result = _run(workspace, timeout_seconds=20)
    assert result.status == "passed", result
    assert result.isolation.verified


def test_live_process_limit(tmp_path: Path) -> None:
    workspace = _workspace(
        tmp_path,
        """import subprocess

def test_pid_limit():
    children = []
    blocked = False
    try:
        for _ in range(64):
            try:
                children.append(subprocess.Popen(['python', '-c', 'import time; time.sleep(10)']))
            except OSError:
                blocked = True
                break
        assert blocked
    finally:
        for child in children:
            child.terminate()
""",
    )
    assert _run(workspace, pids=16, timeout_seconds=30).status == "passed"


def test_live_memory_limit(tmp_path: Path) -> None:
    workspace = _workspace(
        tmp_path,
        """def test_memory_limit():
    chunks = []
    while True:
        chunks.append(bytearray(8 * 1024 * 1024))
""",
    )
    result = _run(workspace, memory="64m", timeout_seconds=30)
    assert result.status == "infrastructure_error"
    assert result.exit_code in {137, 139}


def test_live_timeout_and_container_cleanup(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, "def test_loop():\n    while True:\n        pass\n")
    result = _run(workspace, timeout_seconds=1)
    assert result.status == "timeout"
    remaining = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={result.runtime.container_name}", "-q"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert not remaining.stdout.strip()


def test_live_output_limit(tmp_path: Path) -> None:
    workspace = _workspace(
        tmp_path, "def test_output():\n    print('x' * 10000)\n    assert False\n"
    )
    result = _run(workspace, output_bytes=1024, timeout_seconds=20)
    assert result.status == "failed"
    assert result.output_truncated
    assert len(result.stdout.encode()) + len(result.stderr.encode()) <= 1024


def test_live_concurrent_names_do_not_conflict(tmp_path_factory) -> None:
    roots = [
        _workspace(tmp_path_factory.mktemp(f"concurrent-{index}"), "def test_ok():\n    pass\n")
        for index in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_run, roots))
    assert [result.status for result in results] == ["passed", "passed"]
    assert results[0].runtime.container_name != results[1].runtime.container_name


def test_live_applied_container_configuration(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, "def test_loop():\n    while True:\n        pass\n")
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            _run,
            workspace,
            timeout_seconds=4,
            cpus=0.5,
            memory="64m",
            pids=16,
        )
        container_id = ""
        for _ in range(30):
            found = subprocess.run(
                ["docker", "ps", "--filter", "name=lace-test-", "-q"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
            if found:
                container_id = found[0]
                break
            time.sleep(0.1)
        assert container_id
        inspected = subprocess.run(
            ["docker", "inspect", container_id],
            capture_output=True,
            text=True,
            check=True,
        )
        facts = json.loads(inspected.stdout)[0]
        host = facts["HostConfig"]
        assert host["NanoCpus"] == 500_000_000
        assert host["Memory"] == 64 * 1024 * 1024
        assert host["PidsLimit"] == 16
        assert host["ReadonlyRootfs"] is True
        assert host["NetworkMode"] == "none"
        assert host["Privileged"] is False
        assert host["CapDrop"] == ["ALL"]
        assert "no-new-privileges" in host["SecurityOpt"]
        assert future.result().status == "timeout"


def test_live_pipeline_preserves_original(git_repository: Path, valid_patch: str) -> None:
    test_file = git_repository / "test_calculator.py"
    test_file.write_text(
        "from calculator import divide\n\ndef test_divide():\n    assert divide(6, 3) == 2\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(git_repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(git_repository),
            "-c",
            "user.name=LACE",
            "-c",
            "user.email=lace@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "tests",
        ],
        check=True,
    )
    before = hashlib.sha256((git_repository / "calculator.py").read_bytes()).hexdigest()
    result = RestrictedTestPipeline().run(git_repository, valid_patch)
    assert result.tests is not None and result.tests.status == "passed"
    assert result.workspace.original_unchanged and result.workspace.workspace_cleaned
    assert hashlib.sha256((git_repository / "calculator.py").read_bytes()).hexdigest() == before
