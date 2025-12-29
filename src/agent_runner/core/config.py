from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_CONFIG_PATHS = [
    Path.cwd() / "agent-runner.toml",
    Path.home() / ".config" / "agent-runner" / "agent-runner.toml",
]


@dataclass(frozen=True)
class ExecutionConfig:
    parallelism: int = 1


@dataclass(frozen=True)
class RetentionConfig:
    enabled: bool = False
    days: int = 30


@dataclass(frozen=True)
class OutputConfig:
    write_local: bool = True
    print_stdout: bool = True


@dataclass(frozen=True)
class GithubConfig:
    enabled: bool = False
    repo: str = ""
    default_pr_number: int = 0


@dataclass(frozen=True)
class PreflightConfig:
    """
    strict  -> any ERROR aborts the whole run before any persona executes
    lenient -> personas with ERROR are skipped; others run
    """
    mode: str = "strict"  # "strict" | "lenient"


@dataclass(frozen=True)
class AppConfig:
    execution: ExecutionConfig = ExecutionConfig()
    retention: RetentionConfig = RetentionConfig()
    output: OutputConfig = OutputConfig()
    github: GithubConfig = GithubConfig()
    preflight: PreflightConfig = PreflightConfig()


def _pick_config_path() -> Path | None:
    for p in DEFAULT_CONFIG_PATHS:
        if p.exists():
            return p
    return None


def load_config(path: str | None = None) -> AppConfig:
    """
    Load configuration from TOML. If no path is provided, uses default search paths.
    """
    cfg_path = Path(path) if path else _pick_config_path()
    if not cfg_path:
        return AppConfig()

    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

    exec_ = data.get("execution", {}) or {}
    ret_ = data.get("retention", {}) or {}
    out_ = data.get("output", {}) or {}
    gh_ = data.get("github", {}) or {}
    pf_ = data.get("preflight", {}) or {}

    return AppConfig(
        execution=ExecutionConfig(parallelism=int(exec_.get("parallelism", 1))),
        retention=RetentionConfig(
            enabled=bool(ret_.get("enabled", False)),
            days=int(ret_.get("days", 30)),
        ),
        output=OutputConfig(
            write_local=bool(out_.get("write_local", True)),
            print_stdout=bool(out_.get("print_stdout", True)),
        ),
        github=GithubConfig(
            enabled=bool(gh_.get("enabled", False)),
            repo=str(gh_.get("repo", "")),
            default_pr_number=int(gh_.get("default_pr_number", 0)),
        ),
        preflight=PreflightConfig(
            mode=str(pf_.get("mode", "strict")).strip() or "strict",
        ),
    )
