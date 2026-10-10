"""Interactive command dispatch and application-service coordination."""

import shlex
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from lace import __version__
from lace.config import RepositoryLimits
from lace.context import select_context
from lace.diagnostics import collect_diagnostics
from lace.patches import validate_patch
from lace.repository import RepositoryScanError, scan_repository
from lace.terminal.input import InputComposer
from lace.terminal.render import TerminalRenderer
from lace.terminal.state import SessionState


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _one_argument(value: str) -> str:
    try:
        parts = shlex.split(value, posix=False)
    except ValueError as error:
        raise ValueError(f"invalid quoted argument: {error}") from error
    if len(parts) != 1:
        raise ValueError("expected exactly one path argument")
    return _unquote(parts[0])


class InteractiveSession:
    """Dispatch terminal requests to existing deterministic services."""

    def __init__(
        self,
        *,
        repository: Path | None = None,
        console: Console | None = None,
        prompt: Callable[[], str] | None = None,
        limits: RepositoryLimits | None = None,
    ) -> None:
        self.renderer = TerminalRenderer(console)
        self.input = InputComposer(prompt)
        self.limits = limits or RepositoryLimits()
        self.state = SessionState()
        self._running = True
        if repository is not None:
            self.select_repository(repository, quiet=True)

    @property
    def repository(self) -> Path | None:
        return self.state.repository

    def run(self) -> None:
        self.renderer.welcome(self.state, collect_diagnostics(__version__))
        while self._running:
            try:
                line = self.input.prompt()
                if line.strip():
                    self.renderer.submission(line)
                self.dispatch(line)
            except KeyboardInterrupt:
                self.state.phase = "ready"
                self.renderer.warning("Operation cancelled. Use /exit to leave LACE.")
            except EOFError:
                self.renderer.info("Session closed.")
                break
            except Exception as error:  # defensive UI boundary; services retain typed failures
                self.state.phase = "ready"
                self.renderer.error(f"Unexpected interface failure: {error}")
        self.state.phase = "stopped"

    def dispatch(self, raw: str) -> None:
        line = raw.strip()
        if not line:
            return
        if not line.startswith("/"):
            self.renderer.warning(
                "AI task execution is unavailable until M5. "
                "Use /scan <task> for deterministic context selection."
            )
            return
        command, _, arguments = line.partition(" ")
        handlers: dict[str, Callable[[str], None]] = {
            "/help": self.show_help,
            "/status": self.show_status,
            "/doctor": self.show_doctor,
            "/scan": self.scan,
            "/validate": self.validate,
            "/repo": self.set_repository,
            "/details": self.show_details,
            "/clear": self.clear,
            "/exit": self.exit,
        }
        handler = handlers.get(command.casefold())
        if handler is None:
            self.renderer.error(f"Unknown command: {command}. Type /help.")
            return
        handler(arguments.strip())

    def _reject_arguments(self, command: str, arguments: str) -> bool:
        if not arguments:
            return False
        self.renderer.warning(f"{command} does not accept arguments.")
        return True

    def show_help(self, arguments: str = "") -> None:
        if not self._reject_arguments("/help", arguments):
            self.renderer.help()

    def show_status(self, arguments: str = "") -> None:
        if not self._reject_arguments("/status", arguments):
            self.renderer.status(self.state, collect_diagnostics(__version__))

    def show_doctor(self, arguments: str = "") -> None:
        if not self._reject_arguments("/doctor", arguments):
            self.renderer.doctor(collect_diagnostics(__version__))

    def show_details(self, arguments: str = "") -> None:
        if not self._reject_arguments("/details", arguments):
            self.renderer.details(self.state.last_activity)

    def select_repository(self, path: Path, *, quiet: bool = False) -> bool:
        try:
            inventory = scan_repository(path, self.limits)
        except (OSError, RepositoryScanError) as error:
            if not quiet:
                self.renderer.error(f"Repository rejected: {error}")
            return False
        self.state.repository = inventory.root
        if not quiet:
            self.renderer.success(f"Repository selected: {inventory.root}")
        return True

    def set_repository(self, arguments: str) -> None:
        if not arguments:
            self.renderer.warning("Usage: /repo <path>")
            return
        try:
            path = Path(_one_argument(arguments)).expanduser()
        except ValueError as error:
            self.renderer.error(f"Invalid repository argument: {error}")
            return
        if not path.exists() or not path.is_dir():
            self.renderer.error("Repository rejected: path is not an existing directory")
            return
        with self.renderer.activity("Validating repository"):
            self.select_repository(path)

    def scan(self, task: str) -> None:
        if self.state.repository is None:
            self.renderer.warning("No active repository. Use /repo <path> first.")
            return
        task = _unquote(task)
        if not task:
            self.renderer.warning("Usage: /scan <task>")
            return
        self.state.phase = "running"
        try:
            with self.renderer.activity("Scanning tracked repository files"):
                inventory = scan_repository(self.state.repository, self.limits)
                selection = select_context(inventory, task, self.limits)
            self.state.last_activity = self.renderer.scan_result(inventory, selection)
        except (OSError, RepositoryScanError, ValueError) as error:
            self.renderer.error(f"Scan failed: {error}")
        finally:
            self.state.phase = "ready"

    def validate(self, arguments: str) -> None:
        if self.state.repository is None:
            self.renderer.warning("No active repository. Use /repo <path> first.")
            return
        if not arguments:
            self.renderer.warning("Usage: /validate <patch>")
            return
        try:
            patch_path = Path(_one_argument(arguments)).expanduser().resolve(strict=True)
            if not patch_path.is_file():
                raise ValueError("patch path is not a file")
            patch_text = patch_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError) as error:
            self.renderer.error(f"Patch could not be read: {error}")
            return
        self.state.phase = "running"
        try:
            with self.renderer.activity(f"Validating {patch_path.name}"):
                result = validate_patch(self.state.repository, patch_text)
            self.state.last_activity = self.renderer.validation_result(patch_path.name, result)
        finally:
            self.state.phase = "ready"

    def clear(self, arguments: str = "") -> None:
        if self._reject_arguments("/clear", arguments):
            return
        self.renderer.clear()
        self.renderer.welcome(self.state, collect_diagnostics(__version__))

    def exit(self, arguments: str = "") -> None:
        if self._reject_arguments("/exit", arguments):
            return
        self._running = False
        self.renderer.info("Session closed.")
