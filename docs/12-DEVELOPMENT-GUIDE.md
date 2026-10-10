# Development and Contribution Guide

## Prerequisites and Setup

Verified initialization environment: Windows 11 PowerShell 5.1, Python 3.14.0, Git 2.45.1, and uv 0.12.9. The supported project baseline is Python 3.12+; Python 3.14 compatibility is verified by tests where available. `rtk`, Pandoc, Poetry, Ruff, and pytest were not initially on `PATH`; uv installs project tools into the environment.

```powershell
git clone <repository-url> LACE
Set-Location LACE
uv sync --dev
uv run lace --help
uv run lace doctor
```

Use uv as the selected package manager. It creates `.venv`; activate it only when desired:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Quality Commands

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run lace --version
```

Tests that require Ollama or restricted containers must use explicit markers and skip with a reason locally; a milestone cannot be accepted when its required suite is skipped.

## Development Practice

Create short branches such as `feat/m2-scanner` or `fix/path-containment`. Keep commits coherent and use imperative subjects. Pull requests state requirement IDs, risk, actual commands/results, security effects, documentation changes, and rollback considerations. Do not mix milestones without approval.

Review checklist: typed boundary contracts; untrusted input limits; no shell command strings; canonical paths; no secret logging; deterministic failures; original-repository integrity; relevant allow/deny tests; accurate docs; minimal dependencies; actual verification recorded.

## Debugging and Security Review

Use run IDs and structured events. Reproduce with fixture repositories and sanitized artifacts; never paste credentials or private source into issues. Security-sensitive changes require threat-model mapping, a negative test, dependency/runtime review, and confirmation that model output cannot gain new authority. Report suspected vulnerabilities privately according to repository policy once one exists.

