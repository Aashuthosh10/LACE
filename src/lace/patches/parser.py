"""Strict parser for the supported text unified-diff subset."""

import re
from dataclasses import dataclass

from lace.patches.models import PatchInfo

_DIFF_HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)$")
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")


class PatchParseError(ValueError):
    """Raised when patch syntax is outside LACE's supported subset."""


@dataclass
class _FileState:
    old_diff: str
    new_diff: str
    old_header: str | None = None
    new_header: str | None = None
    saw_hunk: bool = False


def _header_path(line: str, prefix: str) -> str:
    value = line[len(prefix) :]
    if not value or "\t" in value or " " in value:
        raise PatchParseError("quoted, timestamped, or whitespace-containing paths are unsupported")
    if value == "/dev/null":
        return value
    expected = "a/" if prefix == "--- " else "b/"
    if not value.startswith(expected) or len(value) == 2:
        raise PatchParseError(f"file header must use {expected}<path> or /dev/null")
    return value[2:]


def parse_unified_diff(
    text: str, *, max_bytes: int, max_files: int, max_changed_lines: int
) -> PatchInfo:
    raw = text.encode("utf-8")
    if not text.strip():
        raise PatchParseError("patch is empty")
    if len(raw) > max_bytes:
        raise PatchParseError(f"patch exceeds {max_bytes} bytes")
    if "\x00" in text:
        raise PatchParseError("patch contains a NUL byte")
    if "GIT binary patch" in text or "Subproject commit " in text:
        raise PatchParseError("binary and submodule patches are unsupported")

    states: list[_FileState] = []
    current: _FileState | None = None
    additions = deletions = 0
    in_hunk = False

    for number, line in enumerate(text.splitlines(), start=1):
        match = _DIFF_HEADER.fullmatch(line)
        if match:
            if current is not None and not current.saw_hunk:
                raise PatchParseError(f"file before line {number} has no hunk")
            current = _FileState(match.group(1), match.group(2))
            states.append(current)
            if len(states) > max_files:
                raise PatchParseError(f"patch exceeds {max_files} files")
            in_hunk = False
            continue
        if line.startswith("diff --git "):
            raise PatchParseError(f"malformed diff header at line {number}")
        if current is None:
            if line.strip():
                raise PatchParseError(f"unexpected content before diff header at line {number}")
            continue
        if line.startswith("--- "):
            current.old_header = _header_path(line, "--- ")
            in_hunk = False
        elif line.startswith("+++ "):
            current.new_header = _header_path(line, "+++ ")
            in_hunk = False
        elif line.startswith("@@"):
            if current.old_header is None or current.new_header is None:
                raise PatchParseError(f"hunk precedes file headers at line {number}")
            if not _HUNK_HEADER.fullmatch(line):
                raise PatchParseError(f"malformed hunk header at line {number}")
            current.saw_hunk = True
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            additions += 1
        elif in_hunk and line.startswith("-"):
            deletions += 1
        elif in_hunk and (line.startswith(" ") or line == r"\ No newline at end of file"):
            continue
        elif line.startswith(
            ("index ", "new file mode ", "deleted file mode ", "old mode ", "new mode ")
        ):
            if current.old_header is not None:
                raise PatchParseError(f"metadata appears after file headers at line {number}")
        elif line:
            raise PatchParseError(f"unsupported or malformed line {number}")

        if additions + deletions > max_changed_lines:
            raise PatchParseError(f"patch exceeds {max_changed_lines} changed lines")

    if not states:
        raise PatchParseError("patch has no diff headers")

    targets: list[str] = []
    for state in states:
        if state.old_header is None or state.new_header is None or not state.saw_hunk:
            raise PatchParseError("each file needs old/new headers and at least one hunk")
        if state.old_header not in {state.old_diff, "/dev/null"}:
            raise PatchParseError("old path conflicts with diff header")
        if state.new_header not in {state.new_diff, "/dev/null"}:
            raise PatchParseError("new path conflicts with diff header")
        target = state.new_header if state.new_header != "/dev/null" else state.old_header
        targets.append(target)

    return PatchInfo(tuple(targets), additions, deletions)
