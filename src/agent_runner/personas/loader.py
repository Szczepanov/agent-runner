from __future__ import annotations

from pathlib import Path
import yaml

from agent_runner.personas.models import Persona


def load_persona(name: str, personas_dir: str | None = None) -> Persona:
    """
    Load a persona YAML by name from `personas/<name>.yaml` (repo root by default).
    """
    base = Path(personas_dir) if personas_dir else (Path.cwd() / "personas")
    path = base / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Persona not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    persona = Persona(**data)
    if persona.name != name:
        # allow mismatch but prefer correctness
        pass
    return persona
