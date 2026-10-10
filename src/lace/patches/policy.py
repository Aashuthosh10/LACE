"""Repository-relative target path policy."""

import re
from pathlib import PurePosixPath

_DRIVE = re.compile(r"^[A-Za-z]:")
_SECRET_NAMES = {".env", ".netrc", ".npmrc", ".pypirc", "credentials", "credentials.json"}
_SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def validate_target_path(path: str) -> tuple[str, ...]:
    errors: list[str] = []
    if not path or path == "/dev/null":
        return ("target path is empty or invalid",)
    if "\\" in path:
        errors.append("backslashes are forbidden in patch paths")
    if path.startswith(("/", "//")) or _DRIVE.match(path):
        errors.append("absolute, UNC, and drive paths are forbidden")
    if any(ord(char) < 32 or ord(char) == 127 for char in path):
        errors.append("control characters are forbidden in patch paths")

    parts = PurePosixPath(path).parts
    if ".." in parts or "." in parts:
        errors.append("path traversal and dot segments are forbidden")
    folded = tuple(part.casefold() for part in parts)
    if ".git" in folded:
        errors.append("Git internals are forbidden")
    name = folded[-1] if folded else ""
    if (
        name in _SECRET_NAMES
        or name.startswith(".env.")
        or PurePosixPath(name).suffix in _SECRET_SUFFIXES
    ):
        errors.append("sensitive credential or environment path is forbidden")
    if folded[:2] == (".lace", "policy"):
        errors.append("LACE policy files are forbidden")
    return tuple(errors)
