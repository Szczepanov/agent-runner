# Product Requirements Document (PRD)

## Project Name
**Agent-Runner**

---

## 1. One-line Summary
Agent-Runner is a local-first, agent-agnostic orchestration tool that runs multiple AI personas on a scheduled or on-demand basis, captures their outputs deterministically, and routes results into developer-native workflows such as GitHub PR comments or structured local artifacts.

---

## 2. Problem Statement

AI agents are increasingly used for performance reviews, security audits, architectural checks, and UX feedback. However, most agent platforms are:

- UI-driven and manual
- Difficult to schedule
- Poorly composable into repeatable workflows
- Not auditable or deterministic
- Hard to run with multiple independent personas

As a result, recurring AI-driven reviews are fragile, insights are lost in chat UIs, and agents cannot be treated as reliable automation actors.

---

## 3. Goals & Non-Goals

### Goals
- Automate recurring AI agent workflows
- Support multiple independent personas per run
- Remain agent-provider agnostic
- Run locally (CLI, cron, CI)
- Produce deterministic, reviewable outputs
- Integrate naturally with GitHub-based workflows

### Non-Goals
- Building a hosted SaaS platform
- Creating a new LLM or agent system
- Replacing CI/CD pipelines
- Shipping a full web UI in v1

---

## 4. Target Users

### Primary Users
- Senior engineers and tech leads
- Solo founders with complex codebases
- Teams using AI agents for code review and governance

### Secondary Users
- Security reviewers
- Performance engineers
- Product designers performing UX audits

---

## 5. Core Concepts

### 5.1 Agent Persona
A persona is a declarative definition of an AI role, including:
- Mission and responsibilities
- Scope and constraints
- Allowed and forbidden actions
- Expected output schema

Personas are versioned, reusable, and backend-agnostic.

---

### 5.2 Task
A task defines:
- What should be analyzed or generated
- The input scope (repository, diff, directory, files)
- Output expectations

Tasks are stateless, repeatable, and schedulable.

---

### 5.3 Run
A run is a single execution of one or more personas against a task set at a specific point in time. Each run produces structured artifacts and logs.

---

### 5.4 Output Artifact
Artifacts are deterministic outputs such as:
- Markdown reports
- JSON findings
- Suggested diffs or patches
- GitHub PR comments
- Files written under `.agent-runner/`

---

## 6. Functional Requirements

### FR-1: Agent-Agnostic Execution
- Support multiple agent backends (e.g. Jules, OpenAI-style APIs, local LLMs)
- Backend selection configurable per persona
- Unified abstraction layer for all providers

---

### FR-2: Persona Definitions
- Personas defined in YAML
- Declarative and versionable
- Prompt composition must follow best practices:
  - Explicit role definition
  - Clear constraints
  - Deterministic output schema

---

### FR-3: Scheduling
- Support manual CLI execution
- Support cron-based scheduling
- Support CI-triggered execution
- Scheduling must remain OS-agnostic

---

### FR-4: Output Routing
Outputs must be routable to:
- Local files
- STDOUT
- GitHub PR comments

Routing is configurable per persona.

---

### FR-5: Context & Scope Control
- Full repository analysis
- Diff-only analysis
- Directory-scoped analysis
- File allowlists and denylists

---

### FR-6: Deterministic Runs
- Each run must be:
  - Timestamped
  - Logged
  - Reproducible
- Inputs, prompts, and outputs must be persisted

---

### FR-7: Failure Isolation
- Persona failures must not affect other personas
- Errors captured as structured artifacts

---

## 7. Non-Functional Requirements

### NFR-1: Local-First
- No mandatory cloud dependencies
- Secrets provided via environment variables

### NFR-2: Fast Iteration
- Cold start under 1 second (excluding agent calls)
- Minimal dependency footprint

### NFR-3: Observability
- Structured logs
- Clear run summaries
- Machine-readable output formats

### NFR-4: Extensibility
- Easy addition of:
  - New agent providers
  - New personas
  - New output sinks

---

## 8. Technical Constraints

### Language & Tooling
- Python (newest stable version)
- `uv` for dependency management, environments, and script execution

### Configuration
- Global config: TOML (`agent-runner.toml`)
- Personas: YAML (`personas/*.yaml`)

---

## 9. Persistence & Retention

- All runs stored permanently by default
- Optional pruning configurable via TOML

Example:
```toml
[retention]
enabled = true
days = 30
```

---

## 10. Concurrency Model

- Personas are independent
- Execution modes:
  - Sequential
  - Parallel
- Default parallelism: 1 persona at a time

Config example:
```toml
[execution]
parallelism = 1
```

---

## 11. File System Access

- Agents may write files by default
- Writes restricted to `.agent-runner/` unless explicitly allowed

---

## 12. GitHub Integration

- Simple PR comments only
- No checks, no pass/fail gating
- Human-in-the-loop preserved

---

## 13. Default Personas

Agent-Runner ships with reference personas:
- performance
- security
- ux
- architecture

These are examples and intended to be customized.

---

## 14. Project Structure (Proposed)

```
agent_runner/
├─ core/
│  ├─ runner.py
│  ├─ scheduler.py
│  ├─ context.py
│  └─ results.py
├─ agents/
│  ├─ base.py
│  ├─ jules.py
│  └─ openai.py
├─ personas/
│  ├─ performance.yaml
│  ├─ security.yaml
│  ├─ ux.yaml
│  └─ architecture.yaml
├─ outputs/
├─ cli.py
└─ agent-runner.toml
```

---

## 15. CLI Requirements

Example usage:
```bash
agent-runner run \
  --task daily-review \
  --personas performance,security,ux \
  --context diff \
  --output pr-comment
```

---

## 16. Success Metrics

- Reduction in manual agent runs
- Adoption frequency
- Percentage of findings acted upon
- Reduced regressions (performance, security, UX)

---

## 17. Risks & Mitigations

| Risk | Mitigation |
|----|----|
| Agent output noise | Strict output schemas |
| Prompt drift | Versioned personas |
| Vendor lock-in | Agent abstraction layer |
| Over-automation | Explicit opt-in per repo |

---

## 18. License

The project is licensed under the **MIT License** to maximize adoption and minimize legal friction.

