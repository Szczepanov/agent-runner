# Jules Provider — Agent-Runner

This document describes how Agent-Runner integrates with **Jules** via the Jules REST API, with a strong focus on **developer-friendly UX**, safe defaults, and deterministic behavior.

---

## Overview

The Jules provider allows Agent-Runner personas to:

- Run analysis against a GitHub repository connected in Jules
- Optionally create pull requests (disabled by default)
- Return structured, reviewable Markdown output
- Operate fully headless (CLI, cron, CI)

Jules is treated as an **execution backend**, never as an authority.

---

## Required Environment Variables

### `JULES_API_KEY` ✅ (required)

**Description**
Your Jules API key, used to authenticate all REST API calls.

**How to obtain**
- Jules UI → Settings → API Access

**Example**
```bash
export JULES_API_KEY="AIzaSy..."
```

**Notes**
- Passed via `x-goog-api-key` header
- Keep secret
- One key can be reused across personas and repos

---

### `JULES_SOURCE` ✅ (required)

**Description**
Identifier of the GitHub repository *source* connected in Jules.

**Format**
```
sources/{sourceId}
```

**Example**
```bash
export JULES_SOURCE="sources/123456789"
```

**How to find**
- Open your repo in Jules UI
- Copy the `sources/...` identifier from the URL or API metadata

**Why this exists**
Even if Agent-Runner runs locally, Jules needs an explicit reference to the GitHub repo it controls.

---

## Starting Branch (Improved UX)

Unlike most tools, **Agent-Runner does NOT require you to always set a branch explicitly**.

### How the starting branch is resolved (in order)

1. **CLI flag** `--starting-branch`
2. **Persona override**
   ```yaml
   provider_settings:
     jules:
       starting_branch: "main"
   ```
3. **Environment variable** `JULES_STARTING_BRANCH`
4. **Auto-detection (default)**
   - If inside a git repo → current branch
   - If detached HEAD → default remote branch (e.g. `origin/main`)
5. **Config fallback**
   ```toml
   [jules]
   default_starting_branch = "main"
   ```

If all methods fail, Agent-Runner exits with a clear error and instructions.

---

### `JULES_STARTING_BRANCH` (optional)

**Description**
Explicitly sets the Git branch Jules should start from.

**Example**
```bash
export JULES_STARTING_BRANCH="develop"
```

#### Special value: `auto` ⭐ (recommended)
```bash
export JULES_STARTING_BRANCH="auto"
```

Forces automatic detection even in CI or scripted environments.

---

## Optional Environment Variables

### `JULES_BASE_URL`

Override the Jules API endpoint.

**Default**
```
https://jules.googleapis.com/v1alpha
```

Use only for testing or future API versions.

---

### `JULES_REQUIRE_PLAN_APPROVAL`

Controls whether Agent-Runner auto-approves Jules execution plans.

**Values**
- `true` → auto-approve plans
- `false` → fail if approval is required

**Default**
```
false
```

**Recommendation**
Enable only for trusted, scheduled automation.

---

### `JULES_AUTOMATION_MODE`

Controls whether Jules may create pull requests.

**Allowed values**
- `AUTOMATION_MODE_UNSPECIFIED` (default, analysis only)
- `AUTO_CREATE_PR` (Jules may open a PR)

**Example**
```bash
export JULES_AUTOMATION_MODE="AUTOMATION_MODE_UNSPECIFIED"
```

**Strong recommendation**
Keep PR creation disabled by default.

---

### `JULES_TIMEOUT_S`

Maximum time (in seconds) to wait for a Jules session.

**Default**
```
1200  # 20 minutes
```

Increase for large repos or deep analysis personas.

---

### `JULES_POLL_INTERVAL_S`

Polling interval (seconds) when waiting for session completion.

**Default**
```
2
```

Higher values reduce API calls but slow feedback.

---

## Persona-Level Overrides (Best Practice)

All Jules settings can be overridden per persona:

```yaml
provider: "jules"

provider_settings:
  jules:
    source: "sources/123456789"
    starting_branch: auto
    automation_mode: "AUTOMATION_MODE_UNSPECIFIED"
    require_plan_approval: false
    timeout_s: 1200
    poll_interval_s: 2
```

### Precedence Order
1. Persona `provider_settings.jules.*`
2. CLI flags
3. Environment variables
4. `agent-runner.toml`
5. Auto-detection defaults

---

## Minimal Working Setup

```bash
export JULES_API_KEY="..."
export JULES_SOURCE="sources/123"
# no branch required 🎉

uv run agent-runner run \
  --task daily-review \
  --personas performance,security
```

---

## Design Philosophy

- Agent-Runner **never assumes authority**
- Jules proposals are always:
  - Stored locally
  - Reviewable
  - Optional to apply

> Jules suggests.
> Humans decide.

---

## Troubleshooting

### “Could not determine starting branch”
Run inside a git repo or set one of:
- `--starting-branch`
- `provider_settings.jules.starting_branch`
- `JULES_STARTING_BRANCH` (or `auto`)
- `[jules].default_starting_branch` in `agent-runner.toml`

---

## Security Notes

- Do not expose `JULES_API_KEY` in logs
- Prefer `AUTOMATION_MODE_UNSPECIFIED`
- Keep PR creation explicit and opt-in
