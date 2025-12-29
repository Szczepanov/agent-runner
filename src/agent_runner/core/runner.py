from __future__ import annotations

import concurrent.futures
import json
import os
import time
from pathlib import Path

from agent_runner.core.config import AppConfig
from agent_runner.core.context import build_context
from agent_runner.core.results import PersonaResult, RunResult
from agent_runner.personas.loader import load_persona
from agent_runner.providers.base import PreflightIssue
from agent_runner.providers.registry import get_provider


def _make_run_id() -> str:
    # timestamp + short random suffix (PID + millis)
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}-{int(time.time() * 1000) % 100000}"


def _format_preflight_issues(issues_by_persona: dict[str, list[PreflightIssue]]) -> str:
    lines: list[str] = []
    lines.append("Preflight failed.")
    lines.append("")
    for persona_name in sorted(issues_by_persona.keys()):
        issues = issues_by_persona[persona_name]
        for it in issues:
            lines.append(f"- {persona_name}: {it.level} — {it.message}")
            if it.fix:
                lines.append(f"  Fix: {it.fix}")
    return "\n".join(lines).rstrip()


def _preflight(personas: list[str], config: AppConfig) -> tuple[list[str], str | None]:
    """
    Returns (approved_personas, error_message_or_none).

    strict  -> any ERROR aborts whole run
    lenient -> skip personas that have ERROR
    """
    mode = (config.preflight.mode or "strict").lower()
    if mode not in {"strict", "lenient"}:
        mode = "strict"

    issues_by_persona: dict[str, list[PreflightIssue]] = {}
    approved: list[str] = []

    for name in personas:
        persona = load_persona(name)
        provider = get_provider(persona.provider)
        issues = provider.preflight(persona) or []
        # Normalize levels
        norm: list[PreflightIssue] = []
        for it in issues:
            lvl = (it.level or "ERROR").upper()
            if lvl not in {"ERROR", "WARN"}:
                lvl = "ERROR"
            norm.append(PreflightIssue(level=lvl, message=it.message, fix=it.fix))
        issues = norm

        has_error = any(i.level == "ERROR" for i in issues)
        if issues:
            issues_by_persona[name] = issues

        if not has_error:
            approved.append(name)

    if not issues_by_persona:
        return personas, None

    if mode == "strict":
        return [], _format_preflight_issues(issues_by_persona)

    # lenient: skip error personas, but still show warnings later via stdout from caller if desired
    if not approved:
        return [], _format_preflight_issues(issues_by_persona)

    # Return approved, no hard error
    return approved, None


def _run_one_persona(run_dir: Path, persona_name: str, context_mode: str) -> PersonaResult:
    persona = load_persona(persona_name)
    provider = get_provider(persona.provider)

    persona_dir = run_dir / "personas" / persona.name
    persona_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(context_mode)

    try:
        result_text = provider.run(prompt=persona.prompt, context_text=ctx.text, persona=persona)
        out_path = persona_dir / "output.md"
        out_path.write_text(result_text, encoding="utf-8")
        return PersonaResult(persona=persona.name, ok=True, output_path=out_path)
    except Exception as e:  # noqa: BLE001
        err_path = persona_dir / "error.json"
        err_path.write_text(json.dumps({"error": str(e)}, indent=2), encoding="utf-8")
        return PersonaResult(persona=persona.name, ok=False, output_path=err_path, error=str(e))


def run_personas(
    task: str,
    personas: list[str],
    context_mode: str,
    config: AppConfig,
    pr_number: int | None = None,
    *,
    preflight: bool = True,
) -> RunResult:
    """
    Orchestrate persona runs. If preflight is enabled, validate configuration first.

    IMPORTANT: In strict mode, preflight failure aborts BEFORE any run directory is created.
    """
    approved_personas = personas
    if preflight:
        approved_personas, err = _preflight(personas, config)
        if err:
            raise RuntimeError(err)
        if not approved_personas:
            raise RuntimeError("Preflight left no personas to run.")

    run_id = _make_run_id()
    run_dir = Path.cwd() / ".agent-runner" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "task": task,
                "personas": approved_personas,
                "context_mode": context_mode,
                "parallelism": config.execution.parallelism,
                "pr_number": pr_number,
                "preflight": preflight,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    results: list[PersonaResult] = []

    parallelism = max(1, int(config.execution.parallelism))
    if parallelism == 1:
        for p in approved_personas:
            results.append(_run_one_persona(run_dir, p, context_mode))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallelism) as ex:
            futs = [
                ex.submit(_run_one_persona, run_dir, p, context_mode) for p in approved_personas
            ]
            for f in concurrent.futures.as_completed(futs):
                results.append(f.result())

    # NOTE: GitHub sink intentionally stubbed in skeleton.
    return RunResult(
        run_id=run_id, results=sorted(results, key=lambda r: r.persona), run_dir=run_dir
    )
