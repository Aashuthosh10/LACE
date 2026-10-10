# Security Architecture and Threat Model

## Security Position

Repository content, model output, patches, test code, dependencies, and test output are untrusted. The developer and installed LACE policy are trusted to authorize scope; Git, Ollama, and the container runtime are privileged dependencies whose versions/configuration are recorded. Tests passing does not prove correctness or security.

## Assets and Trust Boundaries

Protected assets are the original repository and history, credentials, host filesystem, processes, network, source confidentiality, audit evidence, and developer intent. Boundaries exist between: CLI input and orchestration; repository/model text and parsers; deterministic policy and advisory risk; host and disposable copy; host and restricted container; verified result and final approved apply.

## Threats and Controls

| Threat | Principal controls | Verification |
|---|---|---|
| Prompt injection in source/tests | Treat text as data, fixed system policy, no model tools, bounded context, never accept policy changes from repository | adversarial fixtures |
| Malformed/binary diff | strict parser, size limits, unsupported-feature denial, Git check | parser/property tests |
| Traversal/absolute/UNC/drive paths | lexical canonicalization plus resolved containment | negative path matrix |
| Symlink/junction escape | inspect each ancestor, reject external/reparse targets, isolated mount | platform tests |
| `.git`/history modification | hard forbidden path policy; Git invoked with argument arrays | policy tests |
| Secret/environment/private-key edit or disclosure | forbidden patterns, content exclusion/redaction, restrictive artifacts | fixtures/log review |
| Unrelated or massive edits | target/count/line/byte limits, context relation advisory, approval | boundary tests |
| Dangerous commands | no model-generated command execution; fixed pytest templates only | command injection tests |
| Malicious pytest/dependency code | rootless container, no network, read-only root, narrow ephemeral mount, non-root, dropped caps, resource limits | isolation probes |
| Sandbox escape/runtime compromise | pinned runtime/images, no daemon socket/devices, patched host, defense in depth; residual risk documented | runtime audit |
| TOCTOU before apply | bind approval to patch/base/status hashes; revalidate immediately | state-change integration test |
| Denial of service | input/output/file/attempt/CPU/RAM/PID/time limits | exhaustion tests |
| Misleading test output | output is untrusted and escaped/redacted; report exit metadata separately | terminal-control fixture |
| Rollback failure | avoid original writes until approval; verify before/after; atomic Git apply; do not overclaim cleanup | integrity tests |

## Copy Isolation vs Restricted Execution

A temporary copy limits where a patch is written and makes cleanup convenient. It does **not** restrict code running from that copy: a test can read home-directory secrets, alter other host files, use network services, spawn processes, or exhaust resources. Therefore:

- M1-M3 may use a verified disposable copy for patch handling but execute no target code.
- M4 must introduce restricted Linux-container execution before enabling pytest.
- Windows process execution in a copied directory is not accepted as the MVP security boundary.
- If required isolation is unavailable, LACE fails closed and reports tests as not run.

This tightens the report's “sandbox copy” implementation detail without overriding its sandbox-first objective (SYN p. 2/19; RPT sections 1.1/1.3). It is an engineering recommendation required by the master prompt.

## Deterministic Policy and Risk

Policy yields allowed/blocked with stable rule IDs. Blocks cannot be lowered by risk score or model claims. Risk is an advisory, explainable score used to focus review; its weights are versioned and measured for false positives/negatives. Neither is called a security proof.

## Network, Filesystem, and Resources

The model gateway talks only to a configured loopback Ollama endpoint by default. The test container has no network. It sees a read-only image and one writable ephemeral work tree, not the original, home directory, credentials, Docker socket, or arbitrary devices. Default limits are 120 seconds, 2 CPUs, 2 GiB, 256 PIDs, and 2 MiB output, subject to recorded configuration.

## Audit, Failure Isolation, and Residual Risk

Every decision records rule/config versions, hashes, timestamps, tool/image versions, and outcomes without secrets. Failures stop progression, kill child processes, retain only configured evidence, and attempt workspace cleanup. Residual risks include container/runtime vulnerabilities, weak tests, compromised dependencies/tools, policy gaps, social engineering at approval, and platform-specific filesystem races.

