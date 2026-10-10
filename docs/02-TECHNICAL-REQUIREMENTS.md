# Technical Requirements

## Platform and Toolchain

- **TR-01:** CPython 3.12 or 3.13 is the supported baseline; Python 3.14 may be used only after dependency verification. Windows development is supported, while restricted untrusted execution targets Linux containers.
- **TR-02:** Git 2.40+, Ollama when model features arrive, and a container runtime for M4 are external tools detected by `lace doctor`.
- **TR-03:** Use a `src/` package, `pyproject.toml`, Typer, Rich, prompt-toolkit, Pydantic 2, pytest, Ruff, and standard logging. Pin compatible lower/upper bounds and lock reproducible environments. Rich and prompt-toolkit are presentation-only dependencies.
- **TR-04:** Minimum hardware is not asserted by the sources. REC: 8 GB RAM for the harness; model-specific RAM/VRAM and disk are reported rather than promised.

## Repository and Context

- **TR-05:** Resolve and validate the repository root, require Git for patch checks, honor configured excludes, never traverse symlinks outside the root, and bound inventory by default to 10,000 files/50 MiB metadata scan.
- **TR-06:** Classify source, test, dependency, configuration, generated, binary, and sensitive paths. Sensitive contents are excluded from prompts by default.
- **TR-07:** Context selection records scores and reasons. Initial signals are path/name/task tokens, imports, test references, and failures. Embeddings are optional and deferred.

## Model and Output

- **TR-08:** Ollama calls use a configured local base URL, model name, temperature, context/output limits, and request timeout. Remote hosts require an explicit future policy decision.
- **TR-09:** Models receive bounded text and cannot invoke filesystem, process, or network tools. Planning and patch output have typed envelopes.
- **TR-10:** A model response must contain exactly one supported unified diff payload; prose fences may be normalized only by a documented parser.

## Patch Validation and Risk

- **TR-11:** Parse `diff --git`, `---`, `+++`, and hunk headers; reject malformed/truncated input, unsupported binary/submodule patches, NUL bytes, and conflicting target declarations.
- **TR-12:** Normalize paths lexically as POSIX repository-relative paths. Reject absolute/drive/UNC paths, empty targets except `/dev/null`, `..`, `.git`, backslash ambiguity, control characters, and escapes after filesystem resolution.
- **TR-13:** Default forbidden targets include credential/environment secrets, private keys, Git internals, and LACE artifact/config policy files. Explicit policy may add, but not silently weaken, rules.
- **TR-14:** Enforce configurable limits (REC defaults): 20 files, 2,000 changed lines, 1 MiB patch, 70% deletion ratio warning. Hard policy blocks and risk scores are independently recorded.
- **TR-15:** Run `git apply --check --recount --whitespace=error` using argument arrays, no shell, in a disposable copy. Validation never runs repository code or changes the original.
- **TR-16:** Risk factors include sensitive/security/dependency/config paths, file count, additions/deletions, new executables, test absence, and suspicious code/command text. Scores inform review; policy alone authorizes progression.

## Workspace, Execution, and Repair

- **TR-17:** Copy isolation protects the original from writes but is not an execution security boundary. Verify copied root, exclude `.git` only when compatible with patch checking, defend against symlinks, and clean up deterministically.
- **TR-18:** Untrusted tests require a rootless Linux container with read-only base/root filesystem, writable ephemeral work mount only, no host socket/devices, network disabled, dropped capabilities, `no-new-privileges`, non-root UID, and CPU/memory/PID/time/output limits.
- **TR-19:** Only administrator-configured pytest command templates are executable. Model-generated commands are prohibited.
- **TR-20:** REC defaults: 120-second test timeout, 2 CPUs, 2 GiB memory, 256 PIDs, 2 MiB captured output, and two repair attempts. Overrides are explicit in the run record.
- **TR-21:** Repair input includes sanitized failing tests, bounded traceback excerpts, previous diff, policy feedback, and task. Every replacement patch repeats the full validation pipeline.
- **TR-22:** Before final apply, re-check repository identity, clean/expected state, base commit/tree hash, patch applicability, and approval token. On mismatch, abort rather than merge implicitly.

## Errors, Security, Performance, and Testability

- **TR-23:** Stable error categories are configuration, repository, model, parse, policy, applicability, isolation, test, approval, apply, cleanup, and internal. Human output omits secrets; JSON retains safe structured detail.
- **TR-24:** Structured logs contain timestamp, level, event, run ID, attempt ID, duration, and redacted fields. Prompts/source are opt-in artifacts with restrictive permissions and retention.
- **TR-25:** No unverified latency benchmark is promised. Each stage records monotonic duration and timeout status; evaluation reports median and p95 over declared hardware.
- **TR-26:** Core parsing/policy logic is pure and injectable. Git, clock, filesystem, model, executor, and approval boundaries have typed protocols.
- **TR-27:** Unit tests cover parsers and policies; integration tests use fixture Git repositories; isolation tests prove network, host path, resource, and timeout restrictions; end-to-end tests cover approval and rollback.
- **TR-28:** Interactive mode retains one validated repository per session, uses multiline input with in-memory command history/completion, calls application services directly, handles interrupt/EOF cleanly, provides bounded operation progress and last-result details, and never treats natural-language input as an implemented AI task.

## Acceptance Criteria

M1 is accepted when `lace --help`, `--version`, and `doctor` work; configuration validates; a valid fixture patch passes parse/path/Git checks in a disposable copy; malformed, traversal, absolute, forbidden, and non-applicable patches fail; the original fixture remains byte-for-byte and Git-status unchanged; Ruff and pytest pass. M1 executes no target repository code. Later milestones use the criteria in `08-IMPLEMENTATION-PLAN.md`.

M3 requires a clean Git root, snapshots the HEAD commit/tree plus hashes and modes of eligible tracked regular files, and rejects symlinks, submodules, unsupported modes, unsafe paths, and configured size/count excesses. Patch content and repository state are revalidated before application. Only `git apply --check` and `git apply` run in the disposable workspace; no repository code is executed. Post-apply changes must exactly equal declared patch targets. Cleanup and original-integrity outcomes are reported independently.

M4 uses the fixed `python -m pytest -q --disable-warnings --maxfail=20` template in a locally installed approved image. Docker runs non-root with no network, a read-only root, dropped capabilities, `no-new-privileges`, bounded CPU/memory/PIDs/time/output, private tmpfs, and only the disposable workspace mounted writable. Missing Linux engine, seccomp, or image fails closed; no pull or installation occurs.
