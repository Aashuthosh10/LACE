import io
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from rich.console import Console

from lace.interactive import InteractiveSession
from lace.terminal.input import InputComposer, create_key_bindings


def terminal(width: int = 80) -> tuple[Console, io.StringIO]:
    output = io.StringIO()
    return Console(file=output, width=width, color_system=None, force_terminal=False), output


def prompts(values: list[str | BaseException]):
    iterator: Iterator[str | BaseException] = iter(values)

    def prompt() -> str:
        value = next(iterator)
        if isinstance(value, BaseException):
            raise value
        return value

    return prompt


def git_status(repository: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_interactive_startup_and_clean_exit(scanning_repository: Path) -> None:
    console, output = terminal()
    session = InteractiveSession(
        repository=scanning_repository,
        console=console,
        prompt=prompts(["/exit"]),
    )
    session.run()
    rendered = output.getvalue()
    assert "LACE" in rendered
    assert "Deterministic read-only tools" in rendered
    assert session.repository == scanning_repository.resolve()
    assert "Repository" in rendered
    assert "Session closed" in rendered


def test_dispatch_reports_invalid_and_unavailable_ai() -> None:
    console, output = terminal()
    session = InteractiveSession(console=console, prompt=prompts([]))
    session.dispatch("/unknown")
    session.dispatch("Fix the discount bug")
    session.dispatch("/scan")
    rendered = output.getvalue()
    assert "Unknown command" in rendered
    assert "AI task execution is unavailable" in rendered
    assert "No active repository" in rendered


def test_repository_selection_with_quoted_path(scanning_repository: Path) -> None:
    console, output = terminal()
    session = InteractiveSession(console=console, prompt=prompts([]))
    session.dispatch(f'/repo "{scanning_repository}"')
    assert session.repository == scanning_repository.resolve()
    assert "Repository selected" in output.getvalue()


def test_scan_integration_is_read_only(scanning_repository: Path) -> None:
    console, output = terminal()
    session = InteractiveSession(
        repository=scanning_repository, console=console, prompt=prompts([])
    )
    before = git_status(scanning_repository)
    session.dispatch('/scan "Fix incorrect discount calculation"')
    assert git_status(scanning_repository) == before
    assert session.state.phase == "ready"
    assert session.state.last_activity is not None
    assert session.state.last_activity.kind == "scan"
    rendered = output.getvalue()
    assert "Selected" in rendered
    assert "src/shop/discount.py" in rendered
    assert "Context" in rendered
    session.dispatch("/details")
    assert "python symbols" in output.getvalue()


def test_patch_validation_integration_is_read_only(
    git_repository: Path, valid_patch: str, tmp_path: Path
) -> None:
    patch = tmp_path / "valid patch.diff"
    patch.write_text(valid_patch, encoding="utf-8")
    console, output = terminal()
    session = InteractiveSession(repository=git_repository, console=console, prompt=prompts([]))
    before = git_status(git_repository)
    session.dispatch(f'/validate "{patch}"')
    assert git_status(git_repository) == before
    rendered = output.getvalue()
    assert "Patch validation" in rendered
    assert "Git applicability" in rendered
    assert "unchanged" in rendered


def test_error_presentation_for_missing_arguments_and_files(scanning_repository: Path) -> None:
    console, output = terminal()
    session = InteractiveSession(
        repository=scanning_repository, console=console, prompt=prompts([])
    )
    session.dispatch("/repo")
    session.dispatch("/validate missing.patch")
    rendered = output.getvalue()
    assert "Usage: /repo" in rendered
    assert "Patch could not be read" in rendered


def test_keyboard_interrupt_and_eof_exit_cleanly() -> None:
    console, output = terminal()
    session = InteractiveSession(
        console=console,
        prompt=prompts([KeyboardInterrupt(), EOFError()]),
    )
    session.run()
    rendered = output.getvalue()
    assert "Operation cancelled" in rendered
    assert "Session closed" in rendered


@pytest.mark.parametrize("width", [20, 32])
def test_help_renders_on_narrow_terminals(width: int) -> None:
    console, output = terminal(width)
    session = InteractiveSession(console=console, prompt=prompts([]))
    session.dispatch("/help")
    assert "/validate" in output.getvalue()


def test_completion_history_and_multiline_configuration() -> None:
    composer = InputComposer(lambda: "")
    completions = list(
        composer.completer.get_completions(
            Document("/st"), CompleteEvent(completion_requested=True)
        )
    )
    assert [completion.text for completion in completions] == ["/status"]
    composer.history.append_string("/status")
    assert composer.history.get_strings() == ["/status"]

    bindings = create_key_bindings()
    key_sequences = [tuple(binding.keys) for binding in bindings.bindings]
    assert sorted(len(sequence) for sequence in key_sequences) == [1, 2]
    assert any(
        str(sequence[0]).endswith("Escape") for sequence in key_sequences if len(sequence) == 2
    )


def test_multiline_submission_is_rendered() -> None:
    console, output = terminal()
    session = InteractiveSession(console=console, prompt=prompts([]))
    session.renderer.submission("first line\nsecond line")
    rendered = output.getvalue()
    assert "first line" in rendered
    assert "second line" in rendered


def test_redirected_input_uses_plain_fallback(monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("/exit\n"))
    composer = InputComposer()
    assert composer.prompt() == "/exit"
