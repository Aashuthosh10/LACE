"""Rich rendering for the inline LACE terminal."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lace import __version__
from lace.context.models import ContextSelection
from lace.execution.models import PipelineResult
from lace.patches.models import ValidationResult
from lace.repository.models import RepositoryInventory
from lace.terminal.state import ActivityDetails, SessionState
from lace.workspace.models import WorkspaceApplyResult


class TerminalRenderer:
    """Render compact, capability-accurate terminal output."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console(no_color=os.getenv("NO_COLOR") is not None)

    def welcome(self, state: SessionState, diagnostics: dict[str, Any]) -> None:
        identity = Text.assemble(("LACE", "bold cyan"), (f"  v{__version__}", "dim"))
        description = Text(
            "Local-first coding engine with deterministic safety controls", style="dim"
        )
        status = self._status_table(state, diagnostics)
        capabilities = Text.from_markup(
            "[green]Available[/]: repository scan, context selection, patch validation\n"
            "[dim]Planned[/]: model tasks (M5), restricted tests (M4), repair (M6)"
        )
        quick = Text("Quick start: /repo <path>  /scan <task>  /help", style="cyan")
        self.console.print(
            Panel(
                Group(identity, description, Text(""), status, Text(""), capabilities, quick),
                border_style="bright_black",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

    def _status_table(self, state: SessionState, diagnostics: dict[str, Any]) -> Table:
        isolation = diagnostics["isolation"]
        ollama = diagnostics["ollama"]
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", no_wrap=True)
        table.add_column(overflow="fold")
        table.add_row("Repository", str(state.repository) if state.repository else "Not selected")
        table.add_row("Model", "Not connected (AI pipeline not implemented)")
        table.add_row(
            "Ollama",
            f"CLI {ollama['status']}; service/model configuration not checked",
        )
        runtime = isolation["runtime"] or "not detected"
        table.add_row("Safety", "Deterministic read-only tools")
        table.add_row("Sandbox", f"{runtime}; detected only, not verified")
        table.add_row("Session", state.phase)
        return table

    def status(self, state: SessionState, diagnostics: dict[str, Any]) -> None:
        self.console.print(self._status_table(state, diagnostics))

    def doctor(self, diagnostics: dict[str, Any]) -> None:
        table = Table(box=box.SIMPLE, header_style="bold", expand=False)
        table.add_column("Capability")
        table.add_column("Detected")
        table.add_column("Integration state", overflow="fold")
        table.add_row("Python", diagnostics["python"]["version"], "ready")
        table.add_row("Git", diagnostics["git"]["version"], diagnostics["git"]["status"])
        table.add_row(
            "Ollama",
            diagnostics["ollama"]["version"],
            "not connected; model not configured or loaded",
        )
        table.add_row(
            "Sandbox",
            diagnostics["isolation"]["version"],
            "runtime detection only; M4 verification pending",
        )
        self.console.print(table)

    def help(self) -> None:
        table = Table(box=box.SIMPLE, header_style="bold", expand=False)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Purpose", overflow="fold")
        for command, purpose in (
            ("/repo <path>", "Select and retain a Git repository"),
            ("/scan <task>", "Scan and rank deterministic Python context"),
            ("/validate <patch>", "Validate a unified diff without changing the repository"),
            ("/workspace <patch>", "Apply a patch only in a disposable workspace"),
            ("/test <patch>", "Apply and run pytest in verified restricted isolation"),
            ("/details", "Inspect details from the last scan or validation"),
            ("/status", "Show compact session and capability status"),
            ("/doctor", "Inspect environment dependencies"),
            ("/clear", "Clear the view and redraw the welcome summary"),
            ("/exit", "Exit and restore the terminal"),
        ):
            table.add_row(command, purpose)
        self.console.print(table)
        self.console.print(
            "[dim]Enter submits. Alt+Enter inserts a newline. Up/Down browse history.[/]"
        )

    def submission(self, value: str) -> None:
        display = value.replace("\n", "\n  ")
        self.console.print(Text.assemble((">", "bold cyan"), (f" {display}", "")))

    @contextmanager
    def activity(self, label: str) -> Iterator[None]:
        with self.console.status(f"[cyan]{label}[/]", spinner="dots"):
            yield

    def scan_result(
        self, inventory: RepositoryInventory, selection: ContextSelection
    ) -> ActivityDetails:
        excluded = sum(inventory.exclusion_counts.values())
        table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        table.add_column(style="bold", no_wrap=True)
        table.add_column()
        table.add_row("Operation", "Repository scan")
        table.add_row("Status", "complete")
        table.add_row("Scanned", str(len(inventory.files)))
        table.add_row("Selected", str(len(selection.files)))
        table.add_row("Excluded", str(excluded))
        table.add_row("Context", f"{selection.context_chars} / configured character budget")
        self.console.print(table)
        for selected in selection.files[:5]:
            self.console.print(f"  [cyan]{selected.path}[/] [dim]score {selected.score}[/]")
        if len(selection.files) > 5:
            self.console.print(f"  [dim]+ {len(selection.files) - 5} more; use /details[/]")
        for warning in selection.warnings:
            self.warning(warning)
        return ActivityDetails(
            "scan",
            "Repository scan",
            {
                "files": selection.to_dict()["selected_files"],
                "exclusions": inventory.exclusion_counts,
                "warnings": list(selection.warnings),
                "context_chars": selection.context_chars,
            },
        )

    def validation_result(self, patch_name: str, result: ValidationResult) -> ActivityDetails:
        policy = "pass" if result.policy_allowed else "blocked"
        table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        table.add_column(style="bold", no_wrap=True)
        table.add_column(overflow="fold")
        table.add_row("Operation", "Patch validation")
        table.add_row("Patch", patch_name)
        table.add_row("Changed files", str(len(result.patch.targets) if result.patch else 0))
        table.add_row("Policy", policy)
        table.add_row("Git applicability", "pass" if result.applicable else "fail")
        table.add_row("Original", "unchanged" if result.original_unchanged else "CHANGED")
        self.console.print(table)
        for error in result.errors:
            self.error(error)
        return ActivityDetails(
            "validation",
            "Patch validation",
            {
                "patch": patch_name,
                "targets": list(result.patch.targets) if result.patch else [],
                "additions": result.patch.additions if result.patch else 0,
                "deletions": result.patch.deletions if result.patch else 0,
                "policy": policy,
                "applicable": result.applicable,
                "original_unchanged": result.original_unchanged,
                "errors": list(result.errors),
            },
        )

    def workspace_result(self, patch_name: str, result: WorkspaceApplyResult) -> ActivityDetails:
        table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        table.add_column(style="bold", no_wrap=True)
        table.add_column(overflow="fold")
        table.add_row("Operation", "Disposable workspace apply")
        table.add_row("Patch", patch_name)
        table.add_row("Status", result.status)
        table.add_row("Policy", "pass" if result.policy_allowed else "BLOCK")
        table.add_row("Risk", f"{result.risk.score}/100 {result.risk.level} (advisory)")
        table.add_row("Apply", "pass" if result.applied else "not applied")
        table.add_row("Changed", ", ".join(result.changed_files) or "none")
        table.add_row("Original", "unchanged" if result.original_unchanged else "CHANGED")
        table.add_row("Cleanup", "pass" if result.workspace_cleaned else "not required/failed")
        self.console.print(table)
        for error in result.errors:
            self.error(error)
        if result.cleanup_error:
            self.error(f"Cleanup: {result.cleanup_error}")
        return ActivityDetails("workspace", "Workspace apply", result.to_dict())

    def test_result(self, patch_name: str, result: PipelineResult) -> ActivityDetails:
        tests = result.tests
        table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        table.add_column(style="bold", no_wrap=True)
        table.add_column(overflow="fold")
        table.add_row("Operation", "Restricted pytest")
        table.add_row("Patch", patch_name)
        table.add_row("Workspace", result.workspace.status)
        table.add_row("Isolation", "verified" if tests and tests.isolation.verified else "BLOCKED")
        table.add_row("Tests", tests.status if tests else "not run")
        table.add_row("Runtime", f"{tests.duration_seconds:.2f}s" if tests else "n/a")
        table.add_row("Cleanup", "pass" if result.workspace.workspace_cleaned else "failed")
        self.console.print(table)
        if tests:
            for failure in tests.failure_summary:
                self.error(failure)
        return ActivityDetails("test", "Restricted pytest", result.to_dict())

    def details(self, activity: ActivityDetails | None) -> None:
        if activity is None:
            self.warning("No scan or validation details are available yet.")
            return
        self.console.print(f"[bold]{activity.title} details[/]")
        if activity.kind == "scan":
            for file in activity.payload["files"]:
                reasons = "; ".join(file["reasons"])
                self.console.print(f"  [cyan]{file['path']}[/] score {file['score']}: {reasons}")
            for reason, count in activity.payload["exclusions"].items():
                self.console.print(f"  excluded {reason}: {count}")
        elif activity.kind == "validation":
            self.console.print(f"  patch: {activity.payload['patch']}")
            self.console.print(f"  targets: {', '.join(activity.payload['targets']) or 'none'}")
            self.console.print(
                f"  changes: +{activity.payload['additions']} -{activity.payload['deletions']}"
            )
            for error in activity.payload["errors"]:
                self.error(error)
        else:
            for finding in activity.payload["risk"]["findings"]:
                self.console.print(
                    f"  {finding['rule_id']} +{finding['points']}: {finding['reason']}"
                )
            for error in activity.payload["errors"]:
                self.error(error)

    def info(self, message: str) -> None:
        self.console.print(f"[cyan]Info:[/] {message}")

    def success(self, message: str) -> None:
        self.console.print(f"[green]Done:[/] {message}")

    def warning(self, message: str) -> None:
        self.console.print(f"[yellow]Warning:[/] {message}")

    def error(self, message: str) -> None:
        self.console.print(f"[red]Error:[/] {message}")

    def clear(self) -> None:
        self.console.clear()
