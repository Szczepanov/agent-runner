# ADR-001 — Agent-Runner Architecture & Execution Model

- **Status:** Accepted
- **Date:** 2025-12-29
- **Owner:** Agent-Runner maintainers
- **Applies to:** Agent-Runner v1

---

## Context

Agent-Runner is a local-first orchestration tool that runs multiple AI **personas** (e.g., performance, security, UX) on demand or on a schedule, captures outputs deterministically, and routes results to developer-native destinations (local artifacts and GitHub PR comments).

We need an architecture that:

- Remains **agent-provider agnostic**
- Runs **locally** (CLI, cron, CI) with minimal dependencies
- Produces **auditable, deterministic artifacts**
- Supports **multiple personas** per run with **no shared context**
- Allows configurable **parallelism** (default = 1)

---

## Decision

### 1) Configuration & Persona Definitions

- **Global configuration:** TOML (`agent-runner.toml`)
- **Personas:** YAML (`personas/*.yaml`)

**Rationale:** TOML is strict and tool-friendly; YAML is expressive for prompt templates and constraints.

---

### 2) Execution Model (Runs, Tasks, Personas)

Agent-Runner is built around:

- **Run**: A single invocation containing one or more personas applied to a task set at a point in time.
- **Task**: Defines scope and intent (e.g., “daily-review”), and chooses context mode (repo, diff, directory, allow/deny lists).
- **Persona**: A declarative role contract (mission, constraints, output schema, backend selection).

**Key rule:** Personas are **independent**; there is **no shared context** passed between personas unless explicitly implemented by a future ADR.

---

### 3) Concurrency

- Configurable concurrency via:
  ```toml
  [execution]
  parallelism = 1
  ```
- **Default:** `parallelism = 1` (sequential execution)
- If `parallelism > 1`, personas run concurrently but still independently.

---

### 4) Provider Abstraction Layer

Introduce a provider interface:

- `AgentProvider` (abstract base)
  - `run(prompt, context, settings) -> ProviderResult`

Backends implement this interface (e.g., `JulesProvider`, `OpenAIProvider`, `LocalLLMProvider`).

The core runner does not depend on provider specifics, only on the interface.

---

### 5) Context Assembly

Context is assembled before provider calls and may include:

- Full repository snapshot (bounded by allow/deny rules)
- Diff-only input
- Directory-scoped input
- Metadata (repo info, branch, PR number if available)

Context assembly must be deterministic and stored alongside artifacts.

---

### 6) Output Artifacts & Routing

Outputs are always written to disk under:

- `.agent-runner/runs/<run_id>/...`

Artifacts include:

- `run.json` (run metadata)
- `inputs/` (context snapshot references)
- `personas/<persona_name>/output.md` (primary output)
- `personas/<persona_name>/output.json` (structured output, if applicable)
- `personas/<persona_name>/error.json` (if failed)
- `logs/` (structured logs)

**Routing (v1):**
- Local artifacts (always)
- STDOUT (optional)
- GitHub PR comments (optional)

GitHub integration is **comments only** (no Checks / gating).

---

### 7) File System Write Policy

- **Default:** agents may write files
- **Constraint:** by default, writes are restricted to `.agent-runner/` (sandbox).
- Any write outside the sandbox requires explicit configuration (future extension).

---

### 8) Retention

- Store past runs permanently by default
- Optional pruning:
  ```toml
  [retention]
  enabled = true
  days = 30
  ```

Pruning is a local operation that deletes run directories older than the threshold.

---

## Consequences

### Positive

- Clear separation of concerns:
  - runner (orchestration)
  - providers (agent backends)
  - context (input assembly)
  - sinks (outputs / routing)
- Auditable, deterministic results
- Simple operational model (CLI + cron + CI)
- Easy to extend with new providers and sinks

### Negative / Tradeoffs

- No shared context means:
  - Personas can duplicate work (e.g., both reading same files)
  - No “panel discussion” aggregation in v1 (can be added later as a separate orchestration layer)
- Default parallelism = 1 prioritizes determinism and debuggability over speed

---

## Alternatives Considered

### A) Shared Context / Multi-agent “conversation”
Rejected for v1: introduces hidden coupling, non-determinism, harder debugging, and increases prompt drift risk.

### B) GitHub Checks / failing builds
Rejected for v1: can create “AI as authority” and adds complexity; PR comments preserve human-in-the-loop.

### C) No local artifact persistence
Rejected: reduces auditability and makes scheduling and trend analysis harder.

---

## Implementation Notes (v1 Guidance)

- Provide a stable `run_id` scheme (timestamp + random suffix).
- Ensure artifacts are written even when providers fail.
- Keep provider interface minimal; do not leak backend-specific fields into core.
- Make context assembly bounded and deterministic:
  - stable file ordering
  - size limits
  - explicit include/exclude patterns
- Validate persona YAML against a schema (pydantic model) to fail fast.

---

## Follow-ups

- **ADR-002**: Persona schema & output contracts (Markdown + JSON schema expectations)
- **ADR-003**: GitHub PR comment formatting and idempotency strategy (update vs append)
- **ADR-004**: Security posture for secrets handling and sandboxing policy extensions

---
