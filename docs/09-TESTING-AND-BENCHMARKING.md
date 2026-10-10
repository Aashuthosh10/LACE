# Testing and Benchmarking Plan

## Test Strategy

- **Unit:** diff grammar, target reconciliation, path normalization, policy rules, risk weights, redaction, configuration, metric calculations.
- **Integration:** temporary Git repositories, applicability, workspace lifecycle, dirty-state preservation, report persistence, fake Ollama, container adapter.
- **Security:** traversal/absolute/UNC/drive paths, `.git`, credentials, symlinks/junctions, oversized diffs, command injection, terminal escapes, network/host reads, process/resource limits, TOCTOU.
- **End to end:** invalid output, blocked patch, first-pass success, test failure then repair, exhausted repair, approval denial, changed base, successful apply, cancellation and cleanup.
- **Regression:** every discovered defect receives the smallest durable fixture before or with the fix.

Fixture repositories are tiny, deterministic local Git repositories with committed baselines, intentional bugs, visible tests, hidden held-out tests, manually authored patches, and malicious variants. Fixtures never depend on external network or mutable packages.

## Negative Cases

Reject empty/truncated/multiple ambiguous diffs, NUL/binary/submodule patches, inconsistent headers, nonexistent modifications, forbidden/sensitive paths, traversal, absolute paths, path separator ambiguity, external symlinks, excessive files/lines/bytes, inapplicable hunks, generated commands, missing isolation, timeouts, and repository changes after approval.

## Experimental Comparison

Use the same tasks, repository commits, model build, prompts where applicable, sampling parameters, hardware, time/attempt budget, and random seed across:

1. **Baseline:** one model patch, measured without repair; run only inside the same restricted evaluator.
2. **Validated:** one patch plus deterministic validation/policy and isolated tests.
3. **Full LACE:** validated workflow plus bounded test-feedback repair.

Randomize condition order, keep task-level paired results, separate development and held-out test suites, document exclusions, repeat stochastic trials, and report confidence intervals. Never tune on held-out tests or expose them to the model.

## Metrics

| Metric | Definition |
|---|---|
| Patch validity | syntactically parsed and Git-applicable attempts / generated attempts |
| Test pass | attempts passing declared visible+held-out evaluation / executed attempts |
| Task success | tasks meeting all acceptance tests / attempted tasks |
| Repair success | initially failing tasks later succeeding within budget / initially failing repair-eligible tasks |
| Rollback success | aborted/failed runs with verified original state / runs requiring preservation/restoration |
| Unsafe block | malicious policy fixtures blocked / malicious fixtures |
| Policy false positive | benign fixtures blocked / benign fixtures |
| Policy false negative | malicious fixtures allowed / malicious fixtures |
| Latency | monotonic wall time per stage and end to end; report median/p95 |
| Attempts | generated attempts per task, including invalid outputs |

Also report denominators, skipped/not-run outcomes, patch size, model/tool versions, container digest, CPU/RAM/GPU/OS, configuration hash, commit hashes, and raw per-task results. No invented benchmark or hardware claim is acceptable.

## Gates

CI/local gates are Ruff format/check, pytest unit/integration, and later marked isolation/end-to-end suites. Security controls require both allow and deny tests. A passing suite with skipped required isolation tests does not satisfy M4 acceptance.

## Milestone 3 Verification

M3 tests cover policy/risk separation, deterministic scoring, valid application in a disposable workspace, tracked-link rejection, dirty repositories, secret/traversal/absolute/Windows-style paths, binary and unsupported-mode patches, file/line/byte limits, conflicts, Unicode filenames, patch and source TOCTOU, unexpected post-apply changes, simulated apply failure/interruption/cleanup failure, repeated operations, and byte/status preservation of the original. Tests never execute target repository code.

## Milestone 4 Verification

Unit tests inspect exact Docker controls and classify pass, assertion failure, timeout, and missing-runtime outcomes. Controlled live probes verify network denial, host/root filesystem restrictions, UID/GID 65534, PID and memory limits, timeout termination, bounded output, cleanup, concurrent names, and original integrity. These fixtures execute only through Docker, never the host interpreter. The accepted local image identity and probe results must be re-established after runtime or image changes.
