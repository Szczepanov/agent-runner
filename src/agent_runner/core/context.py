from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextPayload:
    mode: str
    text: str


def build_context(mode: str) -> ContextPayload:
    """
    v1 skeleton: build a simple repo-level context summary.
    Future: diff/dir modes, allow/deny lists, size limits, stable ordering.
    """
    if mode != "repo":
        # skeleton behavior: fallback to repo
        mode = "repo"

    root = Path.cwd()
    # Deterministic: just list top-level files/dirs as a minimal placeholder
    entries = sorted(
        [p.name for p in root.iterdir() if p.name not in {".venv", ".git", ".agent-runner"}]
    )
    text = "Repository root entries:\n" + "\n".join(f"- {e}" for e in entries)
    return ContextPayload(mode=mode, text=text)
