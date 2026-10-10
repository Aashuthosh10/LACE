# Architectural Decisions

## Accepted Decisions

### ADR-001: Python and Standard Packaging
Use typed Python 3.12+ with `pyproject.toml` and `src/` layout because the target ecosystem is Python/pytest. Reject polyglot core and bespoke packaging.

### ADR-002: CLI First
Typer provides discoverable typed commands and fits the approved terminal workflow. A browser/IDE UI is deferred because it expands scope without improving the validation pipeline.

### ADR-003: Modular Monolith
Use in-process modules behind typed interfaces. Reject microservices, distributed queues, and multi-agent frameworks as operationally unjustified.

### ADR-004: Ollama Behind a Model Gateway
Use loopback Ollama for local open-weight inference while keeping prompts/contracts provider-neutral. Reject direct model filesystem/process tools and mandatory cloud APIs.

### ADR-005: Unified Diff and Git
Unified diffs are reviewable and source-required; Git supplies a mature applicability check. LACE parses and policy-checks before Git. Reject unrestricted model file writes and ad hoc search/replace.

### ADR-006: pytest Through Fixed Templates
The initial domain is Python/pytest. Commands come from administrator-controlled templates, never the model. Other frameworks are future adapters.

### ADR-007: Deterministic Blocks Separate from Risk
Policy is binary authority; versioned risk scoring is advisory. Reject score thresholds as the sole safety gate because a low aggregate could mask a categorical violation.

### ADR-008: Restricted Execution, Not Copy-Only Sandboxing
**Source conflict:** SYN pp. 2/19 and RPT 1.1/1.3 describe testing in a repository copy; RPT 1.6 defers Docker/Bubblewrap. A copy protects the original from patch writes but not the host from executing hostile tests. Resolve by using copies for M1-M3 without code execution and requiring rootless restricted Linux containers at M4. Runtime selection (Podman versus Docker rootless) remains open until availability/probe testing; missing isolation fails closed.

### ADR-009: JSON Then SQLite
Versioned JSON is the portable MVP record. Add SQLite as a rebuildable query index only for benchmark volume. Reject PostgreSQL and network services.

### ADR-010: Pydantic Configuration and Environment Overrides
Use typed settings, documented precedence, immutable run snapshots, and `LACE_` environment variables. Repository configuration cannot weaken global policy silently. Reject untyped global dictionaries.

### ADR-011: Structured Standard Logging
Use standard logging with JSON Lines for persisted events and redaction. Reject logging raw prompts/source/secrets by default.

### ADR-012: Model Independence and Future Extensions
Domain contracts do not name a specific model. Tree-sitter, embeddings, languages, CI/GitHub, static analysis, fix memory, and dashboards remain adapters/future work, not core dependencies.

### ADR-013: Clean Tracked-File Workspace Baseline
M3 requires an exact clean Git work tree and copies only eligible tracked regular files into a temporary directory outside the repository. Symlinks, submodules, unsupported modes, unsafe/sensitive/generated paths, and configured limits fail closed or are explicitly excluded before copying. Patch and repository hashes are revalidated before application; observed changes must equal declared targets. This makes integrity evidence deterministic while dirty-tree/final-original application remains deferred to M6.

### ADR-014: Advisory Risk v1
M3 uses deterministic, capped weights for dependency/config/security-related paths, breadth, line volume, deletion concentration, and suspicious added commands, labeled low below 25, moderate below 50, and high otherwise. Risk is review guidance only and cannot override policy. Calibration may revise weights through a versioned future decision without changing this authority boundary.

### ADR-015: Docker With a Preprovisioned Approved Pytest Image
M4 uses Docker Linux containers and an exact administrator-configured local image. Runs never pull images, install packages, accept repository commands, or accept arbitrary Docker flags. Missing engine capabilities or image fails closed. Docker Desktop supplies a Linux VM boundary on Windows; it is not perfect isolation, and acceptance requires live probes for the configured environment.

The accepted v1 image uses the official Python 3.12.12 slim-bookworm amd64 manifest `sha256:2986c55f...130be301`, pytest 9.0.2, and SHA-256-locked wheels. Image labels, OS, architecture, and UID/GID 65534 are verified before execution. The local built image ID is recorded by diagnostics rather than hard-coded because reproducible metadata attestations can alter the manifest-list ID.

## Unresolved Decisions

| ID | Decision | Why unresolved | Deadline/default |
|---|---|---|---|
| OPEN-02 | Default local model and minimum hardware | sources name no model; empirical compatibility required | M5; user config required |
| OPEN-03 | Benchmark task count/repetitions | depends on available compute and adviser methodology | before M7; report power/limitations |
| OPEN-05 | Whether final apply supports dirty trees | correctness/UX trade-off | M6; default reject dirty or changed state |

None blocks M1 because it executes no repository code, contacts no model, and never applies to the original.
