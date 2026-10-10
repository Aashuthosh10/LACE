"""Lightweight deterministic ranking for Python repository context."""

import ast
import re
from pathlib import PurePosixPath

from lace.config import RepositoryLimits
from lace.context.models import ContextSelection, SelectedFile
from lace.repository.models import RepositoryInventory
from lace.repository.scanner import read_inventory_text

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "add",
    "change",
    "correct",
    "fix",
    "for",
    "in",
    "incorrect",
    "of",
    "on",
    "please",
    "the",
    "to",
    "with",
}


def _tokens(value: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value).replace("_", "-")
    return {
        match.group(0).casefold()
        for match in _TOKEN.finditer(expanded)
        if len(match.group(0)) > 1 and match.group(0).casefold() not in _STOP_WORDS
    }


def _python_symbols(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    symbols: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.update(_tokens(node.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.update(_tokens(alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            symbols.update(_tokens(node.module))
    return symbols


def _rank(path: str, text: str, task_tokens: set[str]) -> tuple[int, tuple[str, ...]]:
    stem = PurePosixPath(path).stem.casefold()
    name_tokens = _tokens(stem)
    path_tokens = _tokens(path)
    content_tokens = _tokens(text)
    symbol_tokens = _python_symbols(text)
    reasons: list[str] = []
    score = 0
    if stem in task_tokens:
        score += 6
        reasons.append(f"exact filename: {stem}")
    filename_matches = sorted(task_tokens & name_tokens)
    if filename_matches:
        score += 12 * len(filename_matches)
        reasons.append(f"filename: {', '.join(filename_matches)}")
    path_matches = sorted((task_tokens & path_tokens) - set(filename_matches))
    if path_matches:
        score += 6 * len(path_matches)
        reasons.append(f"path: {', '.join(path_matches)}")
    symbol_matches = sorted(task_tokens & symbol_tokens)
    if symbol_matches:
        score += 8 * len(symbol_matches)
        reasons.append(f"python symbols: {', '.join(symbol_matches)}")
    keyword_matches = sorted((task_tokens & content_tokens) - set(symbol_matches))
    if keyword_matches:
        score += 2 * len(keyword_matches)
        reasons.append(f"keywords: {', '.join(keyword_matches)}")
    return score, tuple(reasons)


def select_context(
    inventory: RepositoryInventory, task: str, limits: RepositoryLimits | None = None
) -> ContextSelection:
    """Rank safe Python files and build a bounded, deterministic context manifest."""
    limits = limits or RepositoryLimits()
    task_tokens = _tokens(task)
    if not task.strip() or not task_tokens:
        raise ValueError("task must contain at least one meaningful word")

    ranked: list[tuple[int, str, tuple[str, ...], str]] = []
    for metadata in inventory.python_files:
        text = read_inventory_text(inventory.root, metadata)
        score, reasons = _rank(metadata.path, text, task_tokens)
        if score > 0:
            ranked.append((score, metadata.path, reasons, text))
    ranked.sort(key=lambda item: (-item[0], item[1].casefold(), item[1]))

    selected: list[SelectedFile] = []
    chunks: list[str] = []
    used = 0
    warnings = list(inventory.warnings)
    for score, path, reasons, text in ranked:
        if len(selected) >= limits.max_selected_files:
            warnings.append("selected-file limit reached")
            break
        chunk = f"### {path}\n{text}"
        separator = 2 if chunks else 0
        if used + separator + len(chunk) > limits.max_context_chars:
            warnings.append(f"context budget excluded {path}")
            continue
        chunks.append(chunk)
        used += separator + len(chunk)
        selected.append(SelectedFile(path, score, reasons, len(chunk)))
    if not ranked:
        warnings.append("no relevant Python files matched the task")
    elif not selected:
        warnings.append("relevant files found but none fit the context budget")
    return ContextSelection(task, tuple(selected), "\n\n".join(chunks), used, tuple(warnings))
