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

## Unresolved Decisions

| ID | Decision | Why unresolved | Deadline/default |
|---|---|---|---|
| OPEN-01 | Rootless Podman vs rootless Docker | host/runtime availability and isolation probes needed | M4; fail closed |
| OPEN-02 | Default local model and minimum hardware | sources name no model; empirical compatibility required | M5; user config required |
| OPEN-03 | Benchmark task count/repetitions | depends on available compute and adviser methodology | before M7; report power/limitations |
| OPEN-04 | Exact risk weights/threshold labels | must be calibrated against fixtures | M3; never override hard policy |
| OPEN-05 | Whether final apply supports dirty trees | correctness/UX trade-off | M6; default reject dirty or changed state |

None blocks M1 because it executes no repository code, contacts no model, and never applies to the original.

