"""End-to-end M1 validation without executing target code."""

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from lace.config import Settings
from lace.patches.assessment import assess_patch
from lace.patches.models import ValidationResult


def _repository_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            digest.update(f"L:{path.relative_to(root).as_posix()}:{path.readlink()}".encode())
        elif path.is_file():
            digest.update(f"F:{path.relative_to(root).as_posix()}".encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _git_root(repository: Path) -> tuple[Path | None, str | None]:
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return None, "repository must be inside a Git work tree"
    return Path(completed.stdout.strip()).resolve(), None


def validate_patch(
    repository: Path, patch_text: str, settings: Settings | None = None
) -> ValidationResult:
    settings = settings or Settings()
    requested = repository.resolve()
    root, root_error = _git_root(requested)
    if root_error or root is None:
        return ValidationResult(
            False, False, False, None, (root_error or "Git root unavailable",), requested, True
        )
    if root != requested:
        return ValidationResult(
            False,
            False,
            False,
            None,
            ("repository path must be the Git work-tree root",),
            root,
            True,
        )

    before = _repository_digest(root)
    assessment = assess_patch(patch_text, settings)
    if assessment.patch is None:
        return ValidationResult(
            False,
            False,
            False,
            None,
            assessment.errors,
            root,
            _repository_digest(root) == before,
        )
    info = assessment.patch
    errors = assessment.errors
    if not assessment.policy_allowed:
        return ValidationResult(
            False,
            False,
            False,
            info,
            errors,
            root,
            _repository_digest(root) == before,
        )

    with tempfile.TemporaryDirectory(prefix="lace-validate-") as temporary:
        copy = Path(temporary) / "repository"
        shutil.copytree(root, copy, symlinks=True)
        completed = subprocess.run(
            ["git", "-C", str(copy), "apply", "--check", "--recount", "--whitespace=error", "-"],
            input=patch_text.encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=30,
        )
        applicable = completed.returncode == 0
        if not applicable:
            detail = completed.stderr.decode("utf-8", errors="replace").strip().splitlines()
            errors = (
                f"Git rejected patch applicability: {detail[0] if detail else 'unknown error'}",
            )

    unchanged = _repository_digest(root) == before
    return ValidationResult(
        applicable and unchanged, True, applicable, info, errors, root, unchanged
    )
