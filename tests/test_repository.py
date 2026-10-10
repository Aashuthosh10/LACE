import hashlib
import subprocess
from pathlib import Path

import pytest

from lace.config import RepositoryLimits
from lace.repository import RepositoryScanError, scan_repository


def repository_state(repository: Path) -> tuple[str, str]:
    status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    index = (repository / ".git" / "index").read_bytes()
    return status, hashlib.sha256(index).hexdigest()


def test_discovers_nested_python_and_tests(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository)
    files = {file.path: file for file in inventory.files}
    assert files["src/shop/discount.py"].kind == "python"
    assert files["src/shop/inventory.py"].kind == "python"
    assert files["tests/test_discount.py"].kind == "test"
    assert files["src/shop/discount.py"].line_count == 3
    assert len(files["src/shop/discount.py"].sha256) == 64


def test_excludes_sensitive_generated_binary_and_symlink(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository)
    exclusions = {item.path: item.reason for item in inventory.exclusions}
    assert exclusions[".env"] == "sensitive_or_unsafe_path"
    assert exclusions[".venv/tracked.py"] == "virtual_environment"
    assert exclusions["__pycache__/tracked.pyc"] == "cache"
    assert exclusions["image.bin"] == "binary"
    assert exclusions["escape.py"] == "symlink"
    assert "ignored.py" not in {file.path for file in inventory.files}


def test_enforces_large_file_and_inventory_limits(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository, RepositoryLimits(max_file_bytes=40))
    assert any(item.reason == "file_too_large" for item in inventory.exclusions)
    with pytest.raises(RepositoryScanError, match="file inventory limit"):
        scan_repository(scanning_repository, RepositoryLimits(max_files=2))
    with pytest.raises(RepositoryScanError, match="byte inventory limit"):
        scan_repository(scanning_repository, RepositoryLimits(max_total_bytes=10))


def test_rejects_subdirectory_and_non_repository(scanning_repository: Path, tmp_path: Path) -> None:
    with pytest.raises(RepositoryScanError, match="work-tree root"):
        scan_repository(scanning_repository / "src")
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(RepositoryScanError, match="Git work tree"):
        scan_repository(outside)


def test_scan_is_deterministic_and_read_only(scanning_repository: Path) -> None:
    before = repository_state(scanning_repository)
    first = scan_repository(scanning_repository)
    second = scan_repository(scanning_repository)
    assert first == second
    assert repository_state(scanning_repository) == before


def test_empty_repository_warns(tmp_path: Path) -> None:
    repository = tmp_path / "empty"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    inventory = scan_repository(repository)
    assert inventory.files == ()
    assert "repository has no tracked files" in inventory.warnings
