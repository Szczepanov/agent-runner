# Agent-Runner 🤖⚙️

**Agent-Runner** is a **local-first, agent-agnostic orchestration tool** for running multiple AI personas (performance, security, UX, architecture, etc.) on demand or on a schedule, producing **deterministic, auditable artifacts**, and optionally posting results as **GitHub PR comments**.

The project is designed to treat AI agents as **repeatable automation actors**, not chat sessions.

---

## Key Principles

- 🏠 **Local-first** — runs on your machine, CI, or cron
- 🧩 **Agent-agnostic** — Jules, OpenAI-style APIs, local LLMs
- 👥 **Multi-persona** — independent agents, no hidden coupling
- 📜 **Auditable** — every run stored with inputs and outputs
- 🧠 **Human-in-the-loop** — PR comments, not failing builds
- ⚙️ **Minimal & extensible** — small core, clear abstractions

---

## What Problem Does It Solve?

Most AI agent tools today are:
- UI-driven
- Hard to schedule
- Not deterministic
- Difficult to compose into workflows
- Poorly auditable

Agent-Runner solves this by:
- Making agent runs **scriptable**
- Persisting results to disk
- Supporting **recurring, multi-persona reviews**
- Integrating naturally with GitHub

---

## Core Concepts

### Persona
A **persona** is a declarative YAML definition of an AI role:
- Mission & responsibilities
- Constraints and boundaries
- Output contract
- Agent provider to use

Example personas:
- Performance reviewer
- Security sentinel
- UX/UI reviewer
- Architecture auditor

Personas are **independent** and do not share context.

---

### Run
A **run** is a single execution of one or more personas against a task and context at a point in time.

Each run produces deterministic artifacts under:
```
.agent-runner/runs/<run_id>/
```

---

### Task
A **task** is a semantic label (e.g. `daily-review`) that groups intent, context mode, and personas.  
In v1, tasks are lightweight and passed via CLI.

---

## Repository Layout

```
agent-runner/
├─ src/agent_runner/        # Python package
│  ├─ core/                # runner, config, context, results
│  ├─ personas/            # persona models & loader
│  ├─ providers/           # agent provider abstractions
│  └─ cli.py               # CLI entrypoint
├─ personas/               # YAML persona definitions
├─ docs/
│  ├─ PRD.md
│  └─ adr/
│     └─ ADR-001-agent-runner-architecture.md
├─ agent-runner.toml       # Global configuration (TOML)
├─ pyproject.toml          # Python + uv config
└─ README.md
```

---

## Installation

Agent-Runner uses **uv** for dependency management.

### Requirements
- Python **3.13+**
- `uv` installed

### Install dependencies
```bash
uv sync
```

---

## Quick Start

### Run default personas
```bash
uv run agent-runner run \
  --task daily-review \
  --personas performance,security,ux \
  --context repo
```

### What happens?
- A new run directory is created
- Each persona runs independently
- Outputs are written to disk
- A summary is printed to stdout

---

## Configuration

### Global config (`agent-runner.toml`)
```toml
[execution]
parallelism = 1

[retention]
enabled = false
days = 30

[output]
write_local = true
print_stdout = true

[github]
enabled = false
repo = "owner/repo"
```

---

## Personas

Personas live in `personas/*.yaml`.

They define:
- Provider (`stub`, `jules`, `openai`, etc.)
- Prompt & constraints
- Output expectations

Example:
```yaml
name: performance
provider: jules
prompt: |
  You are a performance reviewer...
```

Agent-Runner ships with **reference personas**:
- `performance`
- `security`
- `ux`
- `architecture`

They are meant to be **customized**.

---

## Output Artifacts

Each run produces:
```
.agent-runner/runs/<run_id>/
├─ run.json
├─ personas/
│  ├─ performance/output.md
│  ├─ security/output.md
│  └─ ux/output.md
└─ logs/
```

Artifacts are deterministic and auditable.

---

## GitHub Integration (v1)

- **PR comments only**
- No checks, no gating, no pass/fail
- Preserves human authority

Enable via config + `GITHUB_TOKEN`.

---

## License

MIT License — free to use, modify, and distribute.

---

## Roadmap (High-level)

- Real providers (Jules, OpenAI, local LLMs)
- Richer context modes (diff, directory, allow/deny lists)
- Output schemas & validation
- Additional sinks (Slack, files, dashboards)
- Persona composition & higher-level orchestration

---

## Philosophy

> AI agents should behave like reliable automation tools —  
> **observable, repeatable, and bounded** — not magic chat boxes.

Agent-Runner exists to make that practical.
