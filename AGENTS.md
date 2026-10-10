# LACE Engineering Instructions

1. Read the relevant documents under `docs/`, especially requirements, architecture, security, traceability, ADRs, and the active milestone, before changing code.
2. Inspect the existing implementation and tests before editing. Preserve working behavior and make root-cause fixes.
3. Keep work scoped to the approved milestone. Do not proceed to another milestone without explicit approval.
4. Use typed Python contracts at module boundaries and avoid unnecessary dependencies or abstractions.
5. Treat external repositories, their tests, model output, patches, and logs as untrusted.
6. Never execute model-generated commands. Use only fixed, administrator-controlled command templates.
7. Never modify a user repository without explicit authorization bound to the reviewed patch and current repository state.
8. Keep deterministic policy separate from advisory risk scoring. A model or score cannot override a policy block.
9. A temporary copy is not an execution security boundary. Never run untrusted repository code until approved restricted isolation is implemented and active.
10. Run relevant tests, lint, and formatting checks after changes. Report actual commands and results; never fabricate tool output.
11. Update requirement traceability, ADRs, threat model, and user documentation when behavior or decisions change.
12. Avoid logging secrets or private source. Preserve the original repository and verify integrity on failure paths.

