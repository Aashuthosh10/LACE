"""LACE command-line interface."""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from lace import __version__
from lace.config import RepositoryLimits
from lace.context import select_context
from lace.patches import validate_patch
from lace.repository import RepositoryScanError, scan_repository

app = typer.Typer(
    help="Validate AI-generated patches before they can reach a repository.", no_args_is_help=True
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"lace {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
        ),
    ] = None,
) -> None:
    """LACE deterministic patch-validation foundation."""


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


@app.command()
def doctor(
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """Report core readiness and optional integration availability."""
    git_status, git_version = _tool_version("git", ["--version"])
    ollama_status, ollama_version = _tool_version("ollama", ["--version"])
    container = "podman" if shutil.which("podman") else "docker" if shutil.which("docker") else None
    container_status, container_version = (
        _tool_version(container, ["--version"])
        if container
        else ("unavailable", "not found on PATH")
    )
    payload = {
        "lace": __version__,
        "python": {"status": "ready", "version": platform.python_version()},
        "git": {"status": git_status, "version": git_version},
        "ollama": {"status": ollama_status, "version": ollama_version, "required_from": "M5"},
        "isolation": {
            "status": container_status,
            "runtime": container,
            "version": container_version,
            "required_from": "M4",
            "verified": False,
        },
        "m1_ready": git_status == "ready" and sys.version_info >= (3, 12),
        "m2_ready": git_status == "ready" and sys.version_info >= (3, 12),
    }
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(f"LACE         {__version__}")
    typer.echo(f"Python       ready       {payload['python']['version']}")
    typer.echo(f"Git          {git_status:<11} {git_version}")
    typer.echo(f"Ollama       {ollama_status:<11} {ollama_version} (required from M5)")
    typer.echo(
        f"Isolation    {container_status:<11} {container_version} (required from M4; unverified)"
    )
    typer.echo(f"M1 status    {'ready' if payload['m1_ready'] else 'not ready'}")
    typer.echo(f"M2 status    {'ready' if payload['m2_ready'] else 'not ready'}")


@app.command()
def validate(
    patch: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    repository: Annotated[
        Path, typer.Option("--repo", exists=True, file_okay=False, resolve_path=True)
    ],
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """Validate a unified diff in a disposable copy without running target code."""
    try:
        patch_text = patch.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        typer.echo(f"Patch blocked: patch is not valid UTF-8 ({error})", err=True)
        raise typer.Exit(4) from error
    result = validate_patch(repository, patch_text)
    if as_json:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        typer.echo(f"Patch         {'allowed' if result.allowed else 'blocked'}")
        if result.patch:
            typer.echo(f"Targets       {', '.join(result.patch.targets)}")
            typer.echo(f"Changes       +{result.patch.additions} -{result.patch.deletions}")
        typer.echo(f"Applicability {'pass' if result.applicable else 'fail'}")
        typer.echo(f"Original      {'unchanged' if result.original_unchanged else 'CHANGED'}")
        for error in result.errors:
            typer.echo(f"Error         {error}", err=True)
    if not result.allowed:
        raise typer.Exit(5 if result.patch and not result.applicable else 4)


@app.command()
def scan(
    repository: Annotated[
        Path, typer.Option("--repo", exists=True, file_okay=False, resolve_path=True)
    ],
    task: Annotated[str, typer.Option("--task", help="Natural-language coding task.")],
    max_context_chars: Annotated[
        int, typer.Option("--max-context-chars", min=1, help="Maximum selected context size.")
    ] = 50_000,
    max_selected_files: Annotated[
        int, typer.Option("--max-selected-files", min=1, help="Maximum selected file count.")
    ] = 20,
    max_file_bytes: Annotated[
        int, typer.Option("--max-file-bytes", min=1, help="Maximum readable tracked-file size.")
    ] = 262_144,
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")] = False,
) -> None:
    """Inventory tracked files and select deterministic Python context."""
    try:
        limits = RepositoryLimits(
            max_context_chars=max_context_chars,
            max_selected_files=max_selected_files,
            max_file_bytes=max_file_bytes,
        )
        inventory = scan_repository(repository, limits)
        selection = select_context(inventory, task, limits)
    except (RepositoryScanError, ValueError) as error:
        if as_json:
            typer.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            typer.echo(f"Scan failed: {error}", err=True)
        raise typer.Exit(3) from error

    payload = {"repository": inventory.to_dict(), "selection": selection.to_dict()}
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"Repository     {inventory.root}")
    typer.echo(f"Tracked files {inventory.tracked_count}")
    typer.echo(f"Files scanned {len(inventory.files)} ({len(inventory.python_files)} Python)")
    excluded = sum(inventory.exclusion_counts.values())
    typer.echo(f"Excluded      {excluded}")
    for reason, count in inventory.exclusion_counts.items():
        typer.echo(f"  {reason}: {count}")
    typer.echo(f"Selected      {len(selection.files)}")
    for file in selection.files:
        typer.echo(f"  {file.path} [score {file.score}] {'; '.join(file.reasons)}")
    typer.echo(f"Context       {selection.context_chars} characters")
    for warning in selection.warnings:
        typer.echo(f"Warning       {warning}")


if __name__ == "__main__":  # pragma: no cover
    app()
