# LACE

LACE is a local-first, CLI-first harness for controlled AI-assisted changes to Python repositories. Its planned workflow selects repository context, asks an interchangeable Ollama model for a unified diff, independently validates and policy-checks that diff, tests it in restricted isolation, performs bounded repair, and requires developer approval before touching the original repository.

## Current Status

**Milestone 2.5:** optional interactive terminal interface. Running `lace` opens a stateful PowerShell/terminal session over the existing diagnostics, scanning, context-selection, and validation services. Ordinary `doctor`, `validate`, and `scan` commands remain available for scripts. Models, risk scoring, tests of target code, repair, final apply, and benchmarking are not implemented yet.

## Setup

```powershell
uv sync --dev
uv run lace
uv run lace interactive --repo <git-repository>
uv run lace --help
uv run lace doctor
uv run lace scan --repo <git-repository> --task "Fix incorrect discount calculation"
uv run lace validate tests/fixtures/buggy_calculator/fix.patch --repo <git-repository>
```

Interactive commands are `/help`, `/status`, `/doctor`, `/repo <path>`, `/scan <task>`, `/validate <patch>`, `/details`, `/clear`, and `/exit`. Enter submits, Alt+Enter inserts a newline, Tab completes slash commands, and Up/Down browse in-memory history. Natural-language input does not invoke AI; the interface reports that autonomous task execution remains unavailable.

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

## Architecture and Scope

LACE is a typed Python modular monolith. Deterministic host-side policy owns authorization; model and repository content are untrusted. A repository copy is write isolation, not an execution sandbox, so LACE will not run untrusted pytest until the restricted-container milestone.

Start with the [PRD](docs/01-PRD.md), [architecture](docs/03-SYSTEM-ARCHITECTURE.md), [security model](docs/07-SECURITY-AND-THREAT-MODEL.md), [implementation plan](docs/08-IMPLEMENTATION-PLAN.md), and [source traceability](docs/10-REQUIREMENTS-TRACEABILITY.md). The full documentation set is under `docs/`.
