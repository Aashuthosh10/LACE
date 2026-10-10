"""Compatibility facade for LACE's optional interactive terminal."""

from pathlib import Path

from lace.terminal.session import InteractiveSession


def run_interactive(repository: Path | None = None) -> None:
    """Launch the optional inline terminal interface."""
    InteractiveSession(repository=repository).run()


__all__ = ["InteractiveSession", "run_interactive"]
