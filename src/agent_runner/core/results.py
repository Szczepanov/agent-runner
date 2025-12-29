from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PersonaResult:
    persona: str
    ok: bool
    output_path: Path
    error: str | None = None


@dataclass(frozen=True)
class RunResult:
    run_id: str
    results: list[PersonaResult]
    run_dir: Path

    def summary(self) -> str:
        ok = sum(1 for r in self.results if r.ok)
        total = len(self.results)
        return f"run_id={self.run_id} ok={ok}/{total} artifacts={self.run_dir}"
