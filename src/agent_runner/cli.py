from __future__ import annotations

import os

from pathlib import Path
import os
import typer
from rich.console import Console
from rich.panel import Panel

from agent_runner.core.config import load_config
from agent_runner.core.runner import run_personas

app = typer.Typer(add_completion=False, help="Agent-Runner CLI")
console = Console()

def _load_local_env() -> None:
    """
    Load key=value pairs from .local into os.environ
    without overriding already-set variables.
    """
    path = Path.cwd() / ".local"
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

_load_local_env()

@app.command()
def run(
    task: str = typer.Option("daily-review", "--task", help="Task name (semantic)."),
    personas: str = typer.Option(
        "performance,security,ux", "--personas", help="Comma-separated persona names."
    ),
    context: str = typer.Option(
        "repo", "--context", help="Context mode: repo|diff|dir (v1: repo only in skeleton)."
    ),
    pr_number: int = typer.Option(
        0, "--pr-number", help="GitHub PR number for comment sink (optional)."
    ),
    starting_branch: str = typer.Option(
        "",
        "--starting-branch",
        help=(
            "Jules starting branch UX override. "
            "If set, overrides persona/env. Use 'auto' to force auto-detection."
        ),
    ),
    no_preflight: bool = typer.Option(
        False,
        "--no-preflight",
        help="Disable preflight validation (not recommended).",
    ),
) -> None:
    """
    Run one or more personas against a task with a chosen context mode.
    """
    # CLI override for Jules provider (highest precedence)
    if starting_branch.strip():
        os.environ["AGENT_RUNNER_STARTING_BRANCH"] = starting_branch.strip()

    cfg = load_config()
    persona_list = [p.strip() for p in personas.split(",") if p.strip()]

    console.print(
        f"[bold]Agent-Runner[/bold] task={task} context={context} personas={persona_list}"
        + (f" starting_branch={starting_branch.strip()!r}" if starting_branch.strip() else "")
        + ("" if not no_preflight else " preflight=OFF")
    )

    try:
        result = run_personas(
            task=task,
            personas=persona_list,
            context_mode=context,
            config=cfg,
            pr_number=pr_number if pr_number > 0 else None,
            preflight=not no_preflight,
        )
    except RuntimeError as e:
        console.print(Panel(str(e), title="Preflight / Run Error", border_style="red"))
        raise typer.Exit(code=2) from e

    console.print(result.summary())


@app.command()
def version() -> None:
    from agent_runner import __version__

    console.print(__version__)

if __name__ == "__main__":
    app()