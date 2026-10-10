"""prompt-toolkit input composer for the inline terminal."""

import sys
from collections.abc import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output.win32 import NoConsoleScreenBufferError
from prompt_toolkit.styles import Style

COMMANDS = (
    "/help",
    "/status",
    "/doctor",
    "/repo",
    "/scan",
    "/validate",
    "/workspace",
    "/test",
    "/details",
    "/clear",
    "/exit",
)


def create_key_bindings() -> KeyBindings:
    """Enter submits; Alt+Enter inserts a newline."""
    bindings = KeyBindings()

    @bindings.add("enter")
    def submit(event) -> None:  # type: ignore[no-untyped-def]
        event.app.exit(result=event.current_buffer.text)

    @bindings.add("escape", "enter")
    def newline(event) -> None:  # type: ignore[no-untyped-def]
        event.current_buffer.insert_text("\n")

    return bindings


class InputComposer:
    """Own terminal editing, history, completion, and prompt styling."""

    def __init__(self, prompt_override: Callable[[], str] | None = None) -> None:
        self.history = InMemoryHistory()
        self.completer = WordCompleter(COMMANDS, sentence=True)
        self._override = prompt_override
        self._plain_input = False
        self._session: PromptSession[str] | None = None
        if prompt_override is None:
            if not sys.stdin.isatty():
                self._plain_input = True
                return
            options = {
                "history": self.history,
                "auto_suggest": AutoSuggestFromHistory(),
                "completer": self.completer,
                "complete_while_typing": False,
                "multiline": True,
                "key_bindings": create_key_bindings(),
                "style": Style.from_dict({"prompt": "bold #5fd7ff", "marker": "#808080"}),
            }
            try:
                self._session = PromptSession(**options)
            except NoConsoleScreenBufferError:
                self._plain_input = True

    def prompt(self) -> str:
        if self._override is not None:
            return self._override()
        if self._plain_input:
            return input("lace> ")
        if self._session is None:  # pragma: no cover - construction invariant
            raise RuntimeError("input session is unavailable")
        return self._session.prompt(
            HTML("<prompt>lace</prompt><marker> > </marker>"),
            prompt_continuation=lambda _width, _line, _wrap: "     | ",
        )
