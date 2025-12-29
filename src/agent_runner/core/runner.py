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
from agent_runner.providers.registry import get_provider


def _make_run_id() -> str:
    # timestamp + short random suffix (PID + millis)
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}-{int(time.time()*1000)%100000}"


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
) -> RunResult:
    run_id = _make_run_id()
    run_dir = Path.cwd() / ".agent-runner" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "task": task,
                "personas": personas,
                "context_mode": context_mode,
                "parallelism": config.execution.parallelism,
                "pr_number": pr_number,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    results: list[PersonaResult] = []

    parallelism = max(1, int(config.execution.parallelism))
    if parallelism == 1:
        for p in personas:
            results.append(_run_one_persona(run_dir, p, context_mode))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallelism) as ex:
            futs = [ex.submit(_run_one_persona, run_dir, p, context_mode) for p in personas]
            for f in concurrent.futures.as_completed(futs):
                results.append(f.result())

    # NOTE: GitHub sink intentionally stubbed in skeleton.
    return RunResult(run_id=run_id, results=sorted(results, key=lambda r: r.persona), run_dir=run_dir)
