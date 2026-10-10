# Requirements Traceability and Source Comparison

## Source Analysis Method

Both documents were read in full, including introductory/scope/objective sections, all 30 literature entries, references, contents tables, and available figures (neither DOCX contains an embedded diagram). Rendered references use Word page numbers. The synopsis is authoritative for approved objectives; report additions are clarifications unless they alter scope. Neither document is evidence that software exists: wording such as “was developed” is interpreted as proposal language because the repository initially contained only the two DOCX files.

## Source Comparison

| Topic | Synopsis (primary) | Major report (secondary) | Reconciliation |
|---|---|---|---|
| Product | Controlled local patch harness; not full assistant (pp. 1-2) | Same (abstract; 1.1, 1.6) | overlap, retained |
| Initial target | Python + pytest (scope, p. 2) | Same (1.6, p. 12) | overlap |
| Pipeline | scan, select, plan, diff, validate, risk, copy, tests, repair, rollback, metrics (pp. 1-2, 19) | Same with more workflow detail (1.1/1.3) | report clarifies |
| Final apply | not explicit | requires successful verification and user approval (pp. 6-7, 9) | safe clarification, adopted |
| Context method | relevant-file selection only | keywords, filenames, failure matching; optional embeddings (1.3) | deterministic methods MVP; embeddings advanced |
| Risk factors | dangerous/sensitive edits, massive deletion (p. 19) | adds dependency/command/security changes (1.3/1.5) | additive detail |
| Sandbox | “cloned sandbox repository”/copy (pp. 2, 19) | temporary sandbox copy; Docker/Bubblewrap listed as future (1.1/1.6) | copy isolates writes only; restricted container required before tests |
| Metrics | validity, tests, repair, rollback, unsafe block, latency, task success (p. 2) | adds attempts and objective 6 (abstract/1.5) | all retained |
| Scope exclusions | all languages, IDE, production autonomy (p. 2) | same plus autocomplete/enterprise deployment (1.6) | union retained |
| Model | open-weight local model via Ollama (p. 19) | same; examples only in literature | provider fixed, model interchangeable |

## Missing, Inconsistent, and Contradictory Items

- **Missing in both:** exact diff grammar, forbidden path set, resource limits, config precedence, supported Python versions, artifact retention, approval binding, failure exit codes, isolation runtime, model/version, and benchmark sample size. These are labeled REC.
- **Terminology inconsistency:** “local-only” could conflict with package/container/model acquisition. LACE means no mandatory remote AI processing and no repository egress; installation is outside a run.
- **Implementation-tense inconsistency:** synopsis/report sometimes use present/past tense although no implementation was present. Documentation uses proposed/required language.
- **Security contradiction:** calling a repository copy a sandbox suggests execution containment, while the report defers Docker/Bubblewrap. This is unresolved at source level; ADR-008 resolves implementation by forbidding tests until restricted isolation exists.
- **Rollback ambiguity:** deletion of a disposable copy and restoration of an original are different. Reports must state which occurred.
- **Literature quality uncertainty:** entries 25-30 cite broad research categories rather than identifiable publications, and several tool references span future years. They motivate requirements but are not treated as verified empirical evidence.

## Traceability Matrix

| Requirement | Source | Component | Milestone | Verification and acceptance |
|---|---|---|---|---|
| OBJ-01 / NFR-01 | SYN obj. 1 p.19; RPT 1.5 | model/config | M5 | loopback Ollama test; no cloud dependency |
| OBJ-02 / FR-02/03 | SYN obj. 2 p.19; RPT 1.3 | repository/context | M2 | fixtures select expected files and exclude secrets |
| OBJ-03 / FR-04/05 | SYN obj. 3 p.19; RPT 1.1/1.3 | model/patches/Git | M1, M5 | valid diff passes; malformed/inapplicable fail |
| OBJ-04 / FR-06 | SYN obj. 4 p.19; RPT obj. 3 | policy/risk | M1, M3 | malicious path fixtures blocked; factors explained |
| OBJ-05 / FR-07/09 | SYN obj. 5 p.19; RPT obj. 4/5 | workspace/execution/repair | M3, M4, M6 | original integrity, isolated tests, bounded repair |
| OBJ-06 / FR-12 | SYN scope p.2; RPT obj. 6 | reporting/benchmark | M6, M7 | metric definitions and complete denominators |
| FR-01 | SYN scope p.2; RPT 1.1 | CLI | M1, M6 | help/validation then end-to-end CLI tests |
| FR-08 | Source sandbox objective + REC isolation | execution | M4 | network/host/resource probes blocked |
| FR-10 | RPT pp.6-7, 9 | approval/application | M6 | denial changes nothing; hash-bound approval works |
| FR-11 | implied safety/rollback + REC | orchestrator | M3-M6 | timeout/cancel/failure injection preserves original |
| NFR-02 | SYN research gap/objectives pp.18-19 | policy/orchestrator | all | no model authority; policy cannot be overridden |
| NFR-03 | SYN obj.5; RPT pp.6-9 | workspace/Git | M1, M3, M6 | before/after status and content hashes match |
| NFR-04/05 | benchmark objective + REC | contracts/reporting | M1, M7 | schema/tool/config hashes reproduce run |
| NFR-06 | safety goal + REC | config/adapters | M1-M6 | every boundary has tested limits |
| NFR-07 | REC | CLI | M1-M8 | no-color/JSON/keyboard tests |

## Coverage After M2

M2 implements Git-tracked repository inventory, safe file classification, and deterministic bounded Python context selection for OBJ-02 and FR-02/03. Risk scoring, restricted tests, Ollama, repair, final approval/application, rollback restoration, and benchmark execution intentionally remain unimplemented. This is planned milestone scope, not evidence that the MVP is complete. The planned M1-M7 feature set covers every core objective of both sources; M8 validates the integrated MVP.
