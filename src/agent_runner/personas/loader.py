from __future__ import annotations

import os
from pathlib import Path

import yaml

from agent_runner.personas.models import Persona


def _env(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return v if v is not None else default


def _load_yaml_file(path: Path) -> Persona:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Persona(**data)


def _try_load_from_filesystem(name: str, personas_dir: str | None) -> Persona | None:
    base = Path(personas_dir) if personas_dir else (Path.cwd() / "personas")
    path = base / f"{name}.yaml"
    if path.exists():
        return _load_yaml_file(path)
    return None


def _try_load_from_package(name: str) -> Persona | None:
    """
    Built-in personas are shipped in the package under:
      agent_runner/builtin_personas/*.yaml

    This allows running Agent-Runner from any repo without copying personas.
    """
    try:
        from importlib import resources
        pkg = resources.files("agent_runner").joinpath("builtin_personas")
        path = pkg.joinpath(f"{name}.yaml")
        # `path` is a Traversable; read_text works for both source and wheels.
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return Persona(**data)
    except Exception:
        return None
    return None


def load_persona(name: str, personas_dir: str | None = None) -> Persona:
    """
    Load persona YAML.

    Resolution order:
      1) Explicit personas_dir argument (CLI / caller)
      2) Env AGENT_RUNNER_PERSONAS_DIR
      3) ./personas (CWD)
      4) Built-in package personas (agent_runner/builtin_personas)
    """
    env_dir = _env("AGENT_RUNNER_PERSONAS_DIR", "").strip()
    persona = _try_load_from_filesystem(name, personas_dir or (env_dir if env_dir else None))
    if persona:
        return persona

    # Fallback to built-ins
    persona = _try_load_from_package(name)
    if persona:
        return persona

    # Final error message with hints
    base = Path(personas_dir) if personas_dir else (Path.cwd() / "personas")
    raise FileNotFoundError(
        f"Persona not found: {base / (name + '.yaml')}\n"
        f"Tried built-ins: agent_runner/builtin_personas/{name}.yaml\n"
        f"Fix: copy persona into ./personas OR set AGENT_RUNNER_PERSONAS_DIR OR install built-ins."
    )
