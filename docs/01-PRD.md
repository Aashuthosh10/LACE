# LACE Product Requirements Document

## Status and Sources

This document specifies the proposed product; it is not evidence of an existing implementation. The approved scope comes from **SYN**, `LACE- Synopsis.docx` (primary authority), supplemented by **RPT**, `LACE_Major_Project_Report.docx`. **REC** marks an engineering recommendation absent from those sources.

## Executive Summary

LACE is a local-first, CLI-first harness for using interchangeable open-weight coding models through Ollama. It gives the model repository context and accepts a plan and unified diff, while deterministic software retains authority over path policy, patch validation, risk decisions, isolated testing, repair limits, rollback, reporting, and final application. The initial product supports Python repositories using pytest and is intentionally narrower than a general coding assistant (SYN pp. 1-2, 18-19; RPT sections 1.1-1.6, pp. 7-12).

## Problem and Research Motivation

AI-generated changes can be invalid, unrelated, sensitive, destructive, or untested. Cloud services also create confidentiality concerns. Local models improve privacy but may be less reliable. LACE studies whether repository-aware context, deterministic patch controls, isolated tests, and failure feedback improve the safety and reliability of local-model changes (SYN sections 3-5, pp. 18-19; RPT sections 1.2-1.5, pp. 8-11).

## Objectives

| ID | Requirement | Authority |
|---|---|---|
| OBJ-01 | Operate locally with open-weight models through Ollama and no mandatory cloud AI service. | SYN objective 1, p. 19; RPT objective 1, p. 11 |
| OBJ-02 | Scan Python repositories and select relevant source/test context. | SYN objective 2, p. 19; RPT sections 1.1, 1.3 |
| OBJ-03 | Generate and validate unified diffs before repository modification. | SYN objective 3, p. 19; RPT objective 2 |
| OBJ-04 | Detect sensitive edits, dangerous actions, and unusually large changes. | SYN objective 4, p. 19; RPT objective 3 |
| OBJ-05 | Test changes away from the original, repair from test feedback, and support rollback. | SYN objective 5, p. 19; RPT objectives 4-5 |
| OBJ-06 | Measure validity, tests, task/repair/rollback success, unsafe-action blocking, latency, and attempts. | SYN scope, p. 2; RPT objective 6 |

## Users, Personas, and Use Cases

- **Python developer:** requests a small bug fix, reviews a patch and evidence, then explicitly approves application.
- **Student researcher:** compares local models and workflow variants with reproducible task records.
- **Security-conscious maintainer:** verifies that sensitive paths and unsafe actions are blocked before any execution.
- **Evaluator/adviser:** repeats demonstrations and inspects immutable inputs, decisions, and results.

Primary scenarios are fixing a failing test, adding input validation, resolving a simple bug, and making a small refactor (RPT section 1.6, p. 12). Final demonstrations must include valid patch acceptance, malformed/forbidden patch rejection, isolated test failure, repair within a fixed budget, explicit approval, rollback, and comparative metrics.

## Functional Requirements

| ID | Requirement | Source |
|---|---|---|
| FR-01 | Accept a repository and coding task through a CLI. | SYN scope; RPT 1.1 |
| FR-02 | Inventory Python, test, configuration, dependency, and sensitive files without disclosing sensitive content. | SYN objectives 2/4; RPT 1.3 |
| FR-03 | Rank relevant context using deterministic signals; embeddings remain optional. | RPT 1.3 (detail) |
| FR-04 | Request a structured plan followed by a unified diff from an Ollama-hosted model. | SYN introduction/objectives; RPT 1.1 |
| FR-05 | Parse diffs, identify every target, validate paths and format, and check Git applicability before applying. | SYN objective 3; RPT 1.3 |
| FR-06 | Apply deterministic policy blocks separately from advisory numeric risk scoring. | SYN objectives 3/4; REC separation |
| FR-07 | Create a disposable repository copy for patch application and preserve the original during validation. | SYN scope/objective 5; RPT 1.1 |
| FR-08 | Run approved pytest commands only in restricted execution isolation with network/filesystem/resource controls. | Sources require sandbox tests; REC defines adequate isolation |
| FR-09 | Feed bounded, sanitized failure evidence to the model for a configured number of repair attempts. | SYN objective 5; RPT objective 5 |
| FR-10 | Require explicit developer approval before applying a verified patch to the original repository. | RPT pp. 6-7, 9 |
| FR-11 | Abort and retain evidence on cancellation, timeout, policy denial, invalid output, or exhausted repairs. | Implied by rollback/safety; REC details |
| FR-12 | Record inputs, hashes, policy outcomes, test results, attempts, timing, rollback, and final state. | SYN scope/objective 5; RPT objective 6 |

## Nonfunctional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Local-first: repository content and prompts stay local by default; network use is deny-by-default during execution. |
| NFR-02 | Safety authority is deterministic; model output is always untrusted data. |
| NFR-03 | The original working tree is unchanged until explicit approval and a final precondition check. |
| NFR-04 | Runs are reproducible from configuration, tool/model versions, input hashes, and artifacts. |
| NFR-05 | Interfaces and records are typed and versioned; failures are actionable and auditable. |
| NFR-06 | Operations have explicit time, output, attempt, file-count, and patch-size bounds. |
| NFR-07 | CLI output is keyboard accessible, usable without color, and separates status from machine-readable output. |

## MVP and Advanced Scope

The MVP includes FR-01 through FR-12 for small Python/pytest repositories, one local model at a time, unified diffs, deterministic policy, restricted test execution, bounded repair, approval, rollback, and JSON reporting. This reconciles all five synopsis objectives plus the report's explicit benchmark objective.

Advanced requirements are embedding retrieval, Tree-sitter parsing, more languages, static analysis, multi-model experiments, fix memory, GitHub/CI integration, and stronger platform-specific sandboxes (RPT section 1.6). These are not MVP commitments.

## Out of Scope and Limitations

No IDE/autocomplete, cloud requirement, arbitrary-language support, production-autonomous operation, model training, arbitrary model-generated shell execution, multi-agent framework, web dashboard, or enterprise platform is in scope. Passing tests is evidence, not proof of correctness or security. Local-first operation does not prevent malicious repository code from attacking the host unless restricted isolation is actually active.

## Success Criteria and Deliverables

- Each requirement has implementation and verification coverage in `10-REQUIREMENTS-TRACEABILITY.md`.
- The system blocks all policy fixtures for traversal, absolute paths, `.git`, credentials, dangerous commands, and configured patch bounds.
- Demonstration tasks preserve the original until approval and produce complete JSON evidence.
- The evaluation compares baseline generation, validated generation, and full repair under matched tasks/models/configuration.
- Deliverables are source, CLI, tests, fixture repositories, configuration, reports, documentation, and a reproducible demonstration script.

