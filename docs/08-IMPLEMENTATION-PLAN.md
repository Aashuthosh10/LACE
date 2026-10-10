# Implementation Plan

Each milestone delivers a working vertical increment and requires approval before the next begins.

## M1 - Python Foundation and Deterministic Patch Validation

**Objective:** establish packaging, CLI/config/logging, fixtures, and a no-execution validation path. **Prerequisites:** Git and Python. **Work:** create `src/` project; implement `--help`, `--version`, `doctor`, unified-diff parsing, canonical path/forbidden policy, disposable copy, and `git apply --check`; add valid/invalid fixture patches and tests. **Files:** `pyproject.toml`, `src/lace/{cli,config,logging}.py`, `src/lace/patches/`, `tests/`, `tests/fixtures/`. **Deliverables:** installable CLI and JSON-capable validation result. **Tests:** parser/policy units and Git/integrity integration. **Acceptance:** all M1 criteria in technical requirements pass; no target code runs. **Risks:** cross-platform paths, Git behavior, symlinks. **Done:** Ruff and pytest pass and actual output is reported.

## M2 - Repository Scanning and Context Selection

**Objective:** bounded, explainable repository understanding. **Prerequisites:** M1. **Work:** repository identity/inventory, ignores/binary/sensitive classification, token budgeting, deterministic relevance scoring. **Files:** `repository/`, `context/`, contracts. **Deliverables:** `lace scan` and context manifest. **Tests:** large trees, ignores, encodings, symlink escapes, secret exclusion. **Acceptance:** deterministic results and limits; sensitive content absent. **Risks:** scale and false relevance. **Done:** fixture tasks select expected files with reasons.

## M2.5 - Interactive CLI Interface

**Objective:** provide an optional stateful terminal over completed capabilities. **Prerequisites:** M1-M2. **Work:** bare/explicit interactive entry points, separated input/render/state/dispatch, multiline editing, repository session state, Rich presentation, managed progress, prompt-toolkit history/completion, shared diagnostics, last-result details, and honest future-capability status. **Files:** `interactive.py`, `terminal/`, `diagnostics.py`, `cli.py`, tests and CLI documentation. **Deliverables:** `/help`, `/status`, `/doctor`, `/repo`, `/scan`, `/validate`, `/details`, `/clear`, and `/exit`. **Tests:** startup, dispatch, quoted paths, multiline/completion/history, progress, scan/validation integration, narrow layouts, interrupt/EOF, standalone compatibility, JSON output, and repository integrity. **Acceptance:** direct service reuse, clean exit, no code execution or repository writes, all regressions pass. **Risk:** terminal/platform variance. **Done:** PowerShell-compatible inline terminal flow and automated checks pass. This usability increment does not replace or advance the research milestones.

## M3 - Safe Workspace and Patch Processing

**Objective:** patch application entirely away from the original. **Prerequisites:** M1-M2. **Work:** robust workspace lifecycle, apply in copy, integrity snapshots, preview, policy/risk v1, artifacts. **Deliverables:** validated/applied disposable workspace result. **Tests:** dirty repositories, links, limits, Unicode, conflicts, cancellation, cleanup, TOCTOU, unexpected changes, and repeated operations. **Acceptance:** original unchanged for every pre-approval path. **Risks:** permissions, platform semantics, residual filesystem races. **Done:** implemented with clean tracked-file snapshots, deterministic risk v1, CLI/TUI access, fail-closed revalidation, cleanup reporting, and integrity/failure-injection tests. No repository code executes and no original is patched.

## M4 - Isolated Pytest Execution

**Objective:** safely obtain test evidence. **Prerequisites:** M3 and an available Linux container runtime. **Done:** typed Docker executor, digest/hash-pinned approved image, fixed pytest command, fail-closed identity/runtime verification, privilege and resource controls, bounded output, timeout termination, CLI/TUI integration, cleanup orchestration, and controlled live probes. Network, filesystem, non-root, memory, PID, timeout, output, concurrency, cleanup, and original-integrity checks pass on Docker Desktop Linux; no host fallback exists.

## M5 - Ollama Integration

**Objective:** local plan/patch generation through an interchangeable gateway. **Prerequisites:** M2-M4. **Work:** health/model checks, prompt contracts, timeouts, response normalization, provenance. **Deliverables:** model adapter and deterministic fake. **Tests:** unavailable server/model, malformed output, timeout, context limits. **Acceptance:** no cloud traffic; model has no tools. **Risks:** model variance/hardware. **Done:** local fixture produces a patch that enters existing validation.

## M6 - Test-Driven Automatic Repair

**Objective:** bounded repair using concrete failures and explicit approval. **Prerequisites:** M5. **Work:** state machine, sanitization/truncation, attempt budget, full revalidation, approval bound to hashes, controlled final apply/rollback. **Tests:** pass/fail/repair/exhaustion/cancel/state-change. **Acceptance:** no bypass between attempts; original changes only after approval. **Risks:** overfitting and prompt injection in logs. **Done:** end-to-end fixture repair and rollback evidence pass.

## M7 - Benchmarking and Evaluation

**Objective:** fair, reproducible comparison. **Prerequisites:** M6. **Work:** held-out suite, baseline/validated/full variants, seeded configs, metrics/export, optional SQLite index. **Deliverables:** runner, dataset manifest, report. **Tests:** metric math, resume, missing data, repeatability. **Acceptance:** matched tasks/model/hardware and confidence intervals. **Risks:** leakage/small samples. **Done:** complete reproducible experiment package.

## M8 - Hardening, Final Testing, and Demonstration

**Objective:** close security/reliability gaps and package the project. **Prerequisites:** M7. **Work:** threat-model review, dependency/license audit, cross-platform checks, docs, performance, demo rehearsal. **Deliverables:** release candidate and final evidence. **Tests:** full regression, negative security, clean-machine install, demo. **Acceptance:** traceability has no unexplained MVP gaps. **Risks:** environment drift. **Done:** tagged release with known limitations and actual results.
