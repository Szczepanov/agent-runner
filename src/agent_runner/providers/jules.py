from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_runner.personas.models import Persona
from agent_runner.providers.base import AgentProvider, PreflightIssue

# Jules REST API base URL (v1alpha)
DEFAULT_BASE_URL = "https://jules.googleapis.com/v1alpha"

# CLI override env (set by agent_runner.cli)
CLI_STARTING_BRANCH_ENV = "AGENT_RUNNER_STARTING_BRANCH"


@dataclass(frozen=True)
class JulesSettings:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    source: str = ""  # Format: sources/{sourceId}
    starting_branch: str = ""  # GitHub branch name
    require_plan_approval: bool = False
    automation_mode: str = "AUTOMATION_MODE_UNSPECIFIED"  # or AUTO_CREATE_PR
    poll_interval_s: float = 2.0
    timeout_s: float = 20 * 60  # 20 minutes
    page_size: int = 200


def _env(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return v if v is not None else default


def _persona_setting(persona: Persona, key: str) -> Any:
    """
    Personas are loaded with pydantic extra=allow.
    This helper reads optional provider settings stored as:
      provider_settings:
        jules:
          key: value
    or top-level:
      jules:
        key: value
    """
    data = persona.model_dump()

    ps = data.get("provider_settings") or {}
    j = ps.get("jules") or {}
    if isinstance(j, dict) and key in j:
        return j.get(key)

    top = data.get("jules") or {}
    if isinstance(top, dict) and key in top:
        return top.get(key)

    return None


def _auth_headers(api_key: str) -> dict[str, str]:
    # API key is passed via x-goog-api-key header.
    return {
        "x-goog-api-key": api_key,
        "content-type": "application/json; charset=utf-8",
        "accept": "application/json",
    }


def _http_json(method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> Any:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, method=method, headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jules API HTTP {e.code}: {raw}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Jules API request failed: {e}") from e


def _poll_session(settings: JulesSettings, session_name: str) -> dict[str, Any]:
    """Poll session until COMPLETED or FAILED (or timeout)."""
    headers = _auth_headers(settings.api_key)
    deadline = time.time() + settings.timeout_s

    last = None
    while time.time() < deadline:
        last = _http_json("GET", f"{settings.base_url}/{session_name}", headers=headers)
        state = (last or {}).get("state")
        if state in {"COMPLETED", "FAILED"}:
            return last

        # Plan approval flow (optional)
        if settings.require_plan_approval and state == "AWAITING_PLAN_APPROVAL":
            _http_json("POST", f"{settings.base_url}/{session_name}:approvePlan", headers=headers, body={})

        time.sleep(settings.poll_interval_s)

    raise TimeoutError(f"Timed out waiting for session {session_name}. Last: {last}")


def _list_all_activities(settings: JulesSettings, session_name: str) -> list[dict[str, Any]]:
    headers = _auth_headers(settings.api_key)
    page_token = ""
    out: list[dict[str, Any]] = []

    while True:
        qs = f"?pageSize={settings.page_size}"
        if page_token:
            qs += f"&pageToken={page_token}"
        resp = (
            _http_json("GET", f"{settings.base_url}/{session_name}/activities{qs}", headers=headers)
            or {}
        )
        out.extend(resp.get("activities") or [])
        page_token = resp.get("nextPageToken") or ""
        if not page_token:
            break

    # Deterministic ordering (best effort)
    out.sort(key=lambda a: (a.get("createTime", ""), a.get("id", "")))
    return out


def _render_markdown(session: dict[str, Any], activities: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Jules session result")
    lines.append("")
    lines.append(f"- **Session:** `{session.get('name','')}`")
    lines.append(f"- **State:** `{session.get('state','')}`")
    if session.get("url"):
        lines.append(f"- **URL:** {session['url']}")
    lines.append("")

    outputs = session.get("outputs") or []
    pr_urls: list[str] = []
    for o in outputs:
        pr = (o or {}).get("pullRequest")
        if pr and pr.get("url"):
            pr_urls.append(pr["url"])

    if pr_urls:
        lines.append("## Outputs")
        for u in pr_urls:
            lines.append(f"- Pull Request: {u}")
        lines.append("")

    agent_msgs: list[str] = []
    progress: list[tuple[str, str]] = []
    failures: list[str] = []
    patches: list[str] = []

    for a in activities:
        if a.get("agentMessaged") and (a["agentMessaged"] or {}).get("agentMessage"):
            agent_msgs.append(a["agentMessaged"]["agentMessage"])

        if a.get("progressUpdated"):
            pu = a["progressUpdated"] or {}
            title = pu.get("title") or ""
            desc = pu.get("description") or ""
            if title or desc:
                progress.append((title, desc))

        if a.get("sessionFailed") and (a["sessionFailed"] or {}).get("reason"):
            failures.append(a["sessionFailed"]["reason"])

        for art in (a.get("artifacts") or []):
            cs = (art or {}).get("changeSet") or {}
            gp = (cs.get("gitPatch") or {})
            unidiff = gp.get("unidiffPatch")
            if unidiff:
                patches.append(unidiff)

    if progress:
        lines.append("## Progress")
        for t, d in progress:
            if t:
                lines.append(f"- **{t}**")
            if d:
                lines.append(f"  - {d}")
        lines.append("")

    if agent_msgs:
        lines.append("## Agent messages")
        for m in agent_msgs[-10:]:
            lines.append("")
            lines.append(m.strip())
        lines.append("")

    if patches:
        lines.append("## Suggested patch (unidiff)")
        patch = patches[0]
        if len(patch) > 20000:
            patch = patch[:20000] + "\n... (truncated)\n"
        lines.append("```diff")
        lines.append(patch.rstrip("\n"))
        lines.append("```")
        lines.append("")

    if failures:
        lines.append("## Failure reason")
        for r in failures:
            lines.append(f"- {r}")
        lines.append("")

    if not (agent_msgs or patches or pr_urls or progress):
        lines.append("_No messages or artifacts were returned by the API._")

    return "\n".join(lines).rstrip() + "\n"


def _read_config_default_branch() -> str:
    """
    Optional UX: allow `agent-runner.toml` to define:
      [jules]
      default_starting_branch = "main"
    """
    cfg_path = Path.cwd() / "agent-runner.toml"
    if not cfg_path.exists():
        return ""
    try:
        import tomllib  # py3.11+

        data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
        j = data.get("jules", {}) or {}
        return str(j.get("default_starting_branch") or "").strip()
    except Exception:
        # Config parsing should never crash provider; treat as absent.
        return ""


def _run_git(args: list[str]) -> str:
    res = subprocess.run(
        ["git", *args],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "").strip() or "git command failed")
    return (res.stdout or "").strip()


def _auto_detect_branch() -> str:
    """
    Auto-detect starting branch:
    1) current branch (`git rev-parse --abbrev-ref HEAD`)
    2) if detached HEAD -> default remote branch (`refs/remotes/origin/HEAD`)
    """
    try:
        name = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        if name and name != "HEAD":
            return name
    except Exception:
        pass

    # detached HEAD or earlier failed
    try:
        ref = _run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
        # typically: origin/main
        if "/" in ref:
            return ref.split("/", 1)[1]
        return ref
    except Exception:
        return ""


def _resolve_starting_branch(persona: Persona) -> str:
    """
    UX-first resolution order (highest to lowest):
    1) CLI override (AGENT_RUNNER_STARTING_BRANCH)
    2) persona provider_settings.jules.starting_branch
    3) env JULES_STARTING_BRANCH
    4) auto-detection (default)
    5) config fallback [jules].default_starting_branch
    """
    cli_val = _env(CLI_STARTING_BRANCH_ENV, "").strip()
    if cli_val:
        return _auto_detect_branch() if cli_val.lower() == "auto" else cli_val

    p_val = _persona_setting(persona, "starting_branch")
    if isinstance(p_val, str) and p_val.strip():
        v = p_val.strip()
        return _auto_detect_branch() if v.lower() == "auto" else v

    env_val = _env("JULES_STARTING_BRANCH", "").strip()
    if env_val:
        return _auto_detect_branch() if env_val.lower() == "auto" else env_val

    auto = _auto_detect_branch()
    if auto:
        return auto

    cfg_default = _read_config_default_branch()
    if cfg_default:
        return cfg_default

    return ""


def _validate_source_format(source: str) -> bool:
    # Jules expects sources/{id}. id can be numeric or mixed; accept common safe charset.
    return bool(re.fullmatch(r"sources/[A-Za-z0-9_/\-]+", source.strip()))


class JulesProvider(AgentProvider):
    """
    Jules REST API provider.

    Required:
      - JULES_API_KEY
      - JULES_SOURCE (format: sources/{id})

    Starting branch UX:
      - optional; auto-detected by default (see _resolve_starting_branch)
    """

    def preflight(self, persona: Persona) -> list[PreflightIssue]:
        issues: list[PreflightIssue] = []

        api_key = _env("JULES_API_KEY").strip()
        if not api_key:
            issues.append(
                PreflightIssue(
                    level="ERROR",
                    message="Missing JULES_API_KEY.",
                    fix='export JULES_API_KEY="..."',
                )
            )

        source = str(_persona_setting(persona, "source") or _env("JULES_SOURCE")).strip()
        if not source:
            issues.append(
                PreflightIssue(
                    level="ERROR",
                    message="Missing JULES_SOURCE (expected format sources/{id}).",
                    fix='export JULES_SOURCE="sources/123"',
                )
            )
        elif not _validate_source_format(source):
            issues.append(
                PreflightIssue(
                    level="ERROR",
                    message=f"Invalid JULES_SOURCE format: {source!r} (expected sources/{{id}}).",
                    fix='Set JULES_SOURCE like: sources/123',
                )
            )

        # Validate starting branch resolvable (does not guarantee remote branch exists, but catches missing local env/git)
        starting_branch = _resolve_starting_branch(persona)
        if not starting_branch:
            issues.append(
                PreflightIssue(
                    level="ERROR",
                    message="Could not determine starting branch (set --starting-branch, JULES_STARTING_BRANCH, persona override, or run inside a git repo).",
                    fix='Try: --starting-branch auto  OR  export JULES_STARTING_BRANCH="main"',
                )
            )

        # Optional sanity checks (warn only)
        automation_mode = str(_persona_setting(persona, "automation_mode") or _env("JULES_AUTOMATION_MODE", "AUTOMATION_MODE_UNSPECIFIED")).strip()
        if automation_mode == "AUTO_CREATE_PR":
            issues.append(
                PreflightIssue(
                    level="WARN",
                    message="JULES_AUTOMATION_MODE=AUTO_CREATE_PR may create PRs. Consider using AUTOMATION_MODE_UNSPECIFIED by default.",
                    fix='export JULES_AUTOMATION_MODE="AUTOMATION_MODE_UNSPECIFIED"',
                )
            )

        return issues

    def run(self, prompt: str, context_text: str, persona: Persona) -> str:
        api_key = _env("JULES_API_KEY").strip()
        if not api_key:
            raise RuntimeError("Missing JULES_API_KEY environment variable.")

        base_url = str(_persona_setting(persona, "base_url") or _env("JULES_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")

        source = str(_persona_setting(persona, "source") or _env("JULES_SOURCE")).strip()
        if not source:
            raise RuntimeError(
                "Missing Jules source. Set env JULES_SOURCE (format: sources/{id}) "
                "or set persona provider_settings.jules.source."
            )

        starting_branch = _resolve_starting_branch(persona)
        if not starting_branch:
            raise RuntimeError(
                "Could not determine starting branch.\n"
                "Provide one of:\n"
                "- CLI: --starting-branch <name|auto>\n"
                "- Persona: provider_settings.jules.starting_branch\n"
                "- Env: JULES_STARTING_BRANCH=<name|auto>\n"
                "- Config: [jules].default_starting_branch in agent-runner.toml\n"
                "Or run from inside a git repo so auto-detection can succeed."
            )

        require_plan_approval = (
            str(_persona_setting(persona, "require_plan_approval") or _env("JULES_REQUIRE_PLAN_APPROVAL", "false"))
            .lower()
            in {"1", "true", "yes", "y"}
        )
        automation_mode = str(_persona_setting(persona, "automation_mode") or _env("JULES_AUTOMATION_MODE", "AUTOMATION_MODE_UNSPECIFIED"))
        timeout_s = float(_persona_setting(persona, "timeout_s") or _env("JULES_TIMEOUT_S", str(20 * 60)))
        poll_interval_s = float(_persona_setting(persona, "poll_interval_s") or _env("JULES_POLL_INTERVAL_S", "2"))

        settings = JulesSettings(
            api_key=api_key,
            base_url=base_url,
            source=source,
            starting_branch=starting_branch,
            require_plan_approval=require_plan_approval,
            automation_mode=automation_mode,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )

        composed = (
            f"{prompt.strip()}\n\n"
            "----\n"
            "LOCAL CONTEXT (from Agent-Runner)\n"
            "----\n"
            f"{context_text.strip()}\n"
        )

        headers = _auth_headers(settings.api_key)

        session_body = {
            "prompt": composed,
            "sourceContext": {
                "source": settings.source,
                "githubRepoContext": {"startingBranch": settings.starting_branch},
            },
            "requirePlanApproval": settings.require_plan_approval,
            "automationMode": settings.automation_mode,
        }

        created = _http_json("POST", f"{settings.base_url}/sessions", headers=headers, body=session_body) or {}
        session_name = created.get("name")  # e.g., sessions/{id}
        if not session_name:
            raise RuntimeError(f"Unexpected create session response: {created}")

        final_session = _poll_session(settings, session_name)
        activities = _list_all_activities(settings, session_name)
        return _render_markdown(final_session, activities)
