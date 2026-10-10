# Design Brief

## Product Character

LACE should feel like a careful build tool: quiet, inspectable, predictable, and fast to abort. The CLI prioritizes evidence and control over conversational theatrics. It never describes a patch as safe merely because validation or tests passed.

The interactive interface is an inline conversation, not a full-screen application. It preserves terminal scrollback and prints each request and result once. A compact bordered welcome surface is the only panel; operation results use unframed tables and restrained cyan, green, yellow, and red semantic accents.

## Information Architecture

Each operation presents, in order: scope, progress, decision, evidence, and next action. Stable labels (`Repository`, `Patch`, `Policy`, `Risk`, `Tests`, `Original`, `Result`) make repeated runs scannable. Detailed logs and JSON are separate from concise terminal output.

Startup shows identity/version, product purpose, repository, model connection, Ollama detection, safety mode, sandbox verification, implemented capabilities, and quick actions. Detection is never presented as integration: installed Ollama, reachable service, configured model, loaded model, and implemented AI pipeline are distinct states.

## Naming and Commands

- Use verb commands: `doctor`, `validate`, `scan`, `run`, `report`, `benchmark`, `cleanup`.
- Long options are explicit and scriptable; destructive/authorizing actions never hide behind ambiguous short flags.
- Identifiers are sortable and stable. Paths display relative to the selected repository where possible.

## Status Language

| State | Label | Example |
|---|---|---|
| Progress | `running` | `Applicability running` |
| Success | `pass` / `ready` | `Policy pass` |
| Advisory | `warning` | `Risk warning: dependency file changed` |
| Denial | `blocked` | `Policy blocked: path traverses repository root` |
| Operational failure | `failed` | `Isolation failed: container runtime unavailable` |

Spinners appear only on interactive terminals and never replace a stage label. Long work shows elapsed time and bounded attempt counts.

Interactive scan and validation use managed progress that is removed cleanly before result output. The default result is compact; `/details` expands the most recent operation without repeating raw logs. Terminal scrollback handles longer details, while selection and output limits prevent unbounded rendering.

## Patch, Risk, and Test Presentation

Diffs retain familiar unified-diff syntax with additions/deletions colored when possible. Summaries always remain understandable without color. Risk presentation includes a numeric advisory score, level, individual weighted factors, and hard policy decisions in a separate section. Test output starts with counts/duration/status and offers the bounded captured log after it.

## Accessibility and Usability

- Never rely only on color, Unicode glyphs, animation, or terminal width.
- Respect `NO_COLOR`; provide plain output and `--json` for assistive tooling.
- Wrap prose without wrapping diff content; redact credentials and control characters.
- Prompts default to the non-mutating choice, accept keyboard input, and are skipped with a clear error in noninteractive sessions.
- Error messages state what failed, whether the original changed, and the concrete recovery action.
- Enter submits, Alt+Enter inserts a newline, Tab completes slash commands, and Up/Down navigate session history.
- Interactive history remains in memory and is discarded on exit to avoid retaining sensitive tasks or paths.

## Future Dashboard

A read-only local dashboard may later visualize run and benchmark JSON. It is not part of the MVP and must not become an alternate execution authority or require cloud services.
