import shutil
import subprocess
from pathlib import Path

import pytest


def run_git(repository: Path, *arguments: str, input_text: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / "buggy_calculator"
    repository = tmp_path / "repository"
    shutil.copytree(source, repository)
    (repository / "fix.patch").unlink()
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "lace@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "LACE Test"], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "--quiet", "-m", "fixture baseline"], check=True
    )
    return repository


@pytest.fixture
def valid_patch() -> str:
    path = Path(__file__).parent / "fixtures" / "buggy_calculator" / "fix.patch"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def scanning_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "scan-repository"
    (repository / "src" / "shop").mkdir(parents=True)
    (repository / "tests").mkdir()
    (repository / ".venv").mkdir()
    (repository / "__pycache__").mkdir()
    (repository / ".gitignore").write_text(
        ".env\n.venv/\n__pycache__/\nignored.py\n", encoding="utf-8"
    )
    (repository / "src" / "shop" / "discount.py").write_text(
        "class DiscountCalculator:\n"
        "    def calculate_discount(self, price: float) -> float:\n"
        "        return price * 0.10\n",
        encoding="utf-8",
    )
    (repository / "src" / "shop" / "inventory.py").write_text(
        "def count_stock(items: list[str]) -> int:\n    return len(items)\n", encoding="utf-8"
    )
    (repository / "tests" / "test_discount.py").write_text(
        "from shop.discount import DiscountCalculator\n\n"
        "def test_discount() -> None:\n"
        "    assert DiscountCalculator().calculate_discount(100) == 10\n",
        encoding="utf-8",
    )
    (repository / "README.md").write_text("Sample shop project\n", encoding="utf-8")
    (repository / ".env").write_text("SECRET=never-read\n", encoding="utf-8")
    (repository / ".venv" / "tracked.py").write_text("secret = True\n", encoding="utf-8")
    (repository / "__pycache__" / "tracked.pyc").write_bytes(b"\0binary")
    (repository / "ignored.py").write_text("ignored = True\n", encoding="utf-8")
    (repository / "image.bin").write_bytes(b"PNG\0payload")

    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    run_git(repository, "config", "user.email", "lace@example.invalid")
    run_git(repository, "config", "user.name", "LACE Test")
    run_git(repository, "add", ".")
    run_git(
        repository,
        "add",
        "--force",
        ".env",
        ".venv/tracked.py",
        "__pycache__/tracked.pyc",
    )
    run_git(repository, "add", "image.bin")
    link_blob = run_git(repository, "hash-object", "-w", "--stdin", input_text="../outside.py")
    run_git(repository, "update-index", "--add", "--cacheinfo", f"120000,{link_blob},escape.py")
    run_git(repository, "commit", "--quiet", "-m", "scanner fixture")
    return repository
