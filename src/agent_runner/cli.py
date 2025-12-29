from __future__ import annotations

import typer
from rich.console import Console

from agent_runner.core.config import load_config
from agent_runner.core.runner import run_personas

app = typer.Typer(add_completion=False, help="Agent-Runner CLI")
console = Console()


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
) -> None:
    """
    Run one or more personas against a task with a chosen context mode.
    """
    cfg = load_config()
    persona_list = [p.strip() for p in personas.split(",") if p.strip()]
    console.print(f"[bold]Agent-Runner[/bold] task={task} context={context} personas={persona_list}")

    result = run_personas(
        task=task,
        personas=persona_list,
        context_mode=context,
        config=cfg,
        pr_number=pr_number if pr_number > 0 else None,
    )
    console.print(result.summary())


@app.command()
def version() -> None:
    from agent_runner import __version__

    console.print(__version__)
