# System Architecture

## Architectural Style

LACE is a modular monolith. The CLI calls an application orchestrator; domain services operate on typed contracts; adapters isolate Git, Ollama, filesystem, container runtime, clock, and persistence. Dependency flow points inward to contracts and policy. The model has no direct tool authority.

```mermaid
flowchart LR
  U[Developer] --> CLI[Typer CLI]
  CLI --> APP[Task Orchestrator]
  APP --> SCAN[Repository Scanner]
  APP --> CTX[Context Selector]
  APP --> MODEL[Model Gateway]
  APP --> PATCH[Patch Parser and Validator]
  APP --> POLICY[Policy and Risk]
  APP --> WS[Workspace Manager]
  APP --> EXEC[Restricted Test Executor]
  APP --> REPORT[Run Recorder]
  MODEL --> OLLAMA[Local Ollama]
  PATCH --> GIT[Git Adapter]
  EXEC --> CONTAINER[Rootless Linux Container]
  APP --> APPROVE[Explicit Approval]
```

## Components and Interfaces

| Component | Responsibility | Principal interface | Dependencies |
|---|---|---|---|
| `cli` | Parse commands, render output, map exit codes | `main()`, `doctor`, later `run` | application services |
| `config` | Load defaults/file/env and validate | `Settings` | Pydantic |
| `contracts` | Versioned immutable request/result records | models/enums | none |
| `repository` | Identify root, inventory metadata, state hashes | `RepositoryGateway` | filesystem/Git |
| `context` | Score and budget prompt context | `ContextSelector` | inventory |
| `model` | Local inference and response normalization | `ModelGateway` | Ollama HTTP |
| `patches` | Parse diff and derive canonical targets/stats | `parse_unified_diff` | pure domain logic |
| `policy` | Deterministic allow/deny and advisory risk | `evaluate_patch` | contracts/config |
| `workspace` | Disposable copies, integrity, cleanup | `WorkspaceManager` | filesystem |
| `git` | Applicability and controlled application | `GitGateway` | subprocess arrays |
| `execution` | Approved pytest in restricted isolation | `TestExecutor` | container runtime |
| `repair` | Bounded feedback/attempt state machine | `RepairCoordinator` | model/validation |
| `reporting` | JSON artifacts and later SQLite projection | `RunRecorder` | filesystem/storage |

## Interaction and Data Flow

```mermaid
sequenceDiagram
  actor D as Developer
  participant C as CLI
  participant O as Orchestrator
  participant M as Local Model
  participant V as Validator/Policy
  participant W as Workspace
  participant X as Restricted Executor
  D->>C: repository + task
  C->>O: TaskRequest
  O->>M: bounded context + plan schema
  M-->>O: plan then unified diff
  O->>V: untrusted diff
  V-->>O: decision + risk + targets
  O->>W: create disposable copy and apply
  W->>X: approved pytest specification
  X-->>O: bounded TestResult
  alt tests fail and budget remains
    O->>M: sanitized failure + previous attempt
  else verified
    O-->>D: preview, evidence, approval prompt
    D->>O: explicit approval
  end
```

```mermaid
flowchart TD
  T[Task] --> I[Inventory and classify]
  I --> S[Select bounded context]
  S --> P[Generate structured plan]
  P --> D[Generate unified diff]
  D --> A{Parse and canonicalize?}
  A -- no --> F[Record failure]
  A -- yes --> B{Deterministic policy allows?}
  B -- no --> F
  B -- yes --> G{Git apply check?}
  G -- no --> R{Repair budget?}
  G -- yes --> C[Copy workspace and apply]
  C --> X[Restricted pytest]
  X --> Q{Pass?}
  Q -- no --> R
  R -- yes --> D
  R -- no --> Z[Cleanup and failed report]
  Q -- yes --> H[Preview and explicit approval]
  H --> J{Base unchanged?}
  J -- no --> Z
  J -- yes --> K[Controlled final apply and report]
```

## Patch Validation

```mermaid
flowchart LR
  RAW[Raw model text] --> SIZE[Input limits]
  SIZE --> PARSE[Grammar parse]
  PARSE --> PATH[Canonical path checks]
  PATH --> POL[Policy decision]
  POL --> RISK[Advisory risk score]
  RISK --> COPY[Disposable copy]
  COPY --> CHECK[git apply --check]
  CHECK --> RESULT[ValidationResult]
```

Parsing never infers authorization. A valid diff can still be forbidden; a low risk score cannot override a policy block.

## Isolation and Failure Recovery

```mermaid
flowchart TB
  HOST[Host: CLI, policy, original repo] --> COPY[Ephemeral workspace copy]
  COPY --> MOUNT[Writable container work mount]
  IMAGE[Read-only pinned test image] --> CTR[Rootless container]
  MOUNT --> CTR
  CTR --> LIMITS[No network; non-root; caps dropped; CPU/RAM/PID/time limits]
  CTR --> OUT[Bounded stdout/stderr + exit metadata]
  OUT --> HOST
```

```mermaid
stateDiagram-v2
  [*] --> Created
  Created --> Validating
  Validating --> Rejected: parse/policy/applicability
  Validating --> Testing: allowed
  Testing --> Repairing: failed and budget
  Repairing --> Validating
  Testing --> AwaitingApproval: passed
  AwaitingApproval --> Aborted: denied/timeout/base changed
  AwaitingApproval --> Applied: approved and revalidated
  Rejected --> Cleaned
  Aborted --> Cleaned
  Applied --> Cleaned
  Cleaned --> [*]
```

Cleanup is attempted on every terminal path. Workspace deletion is not called rollback; rollback means restoration or non-modification of the original and is verified separately.

## Data Lifecycle

```mermaid
flowchart LR
  INPUT[Task + config + repo identity] --> RUN[Run record]
  INV[Inventory metadata] --> RUN
  PLAN[Plan hash/artifact] --> RUN
  DIFF[Patch hash/artifact] --> ATT[Attempt record]
  DEC[Policy + risk] --> ATT
  TEST[Test result] --> ATT
  ATT --> JSON[Versioned JSON report]
  JSON -. optional projection .-> SQL[Future SQLite]
```

Raw source, prompts, and test output are retained only by explicit configuration; hashes and redacted summaries are the default. See `06-BACKEND-AND-DATA-SCHEMA.md`.

