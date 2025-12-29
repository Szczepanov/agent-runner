from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from agent_runner.personas.models import Persona


@dataclass(frozen=True)
class PreflightIssue:
    """
    A lightweight preflight validation issue.

    - level: "ERROR" blocks execution in strict mode
    - message: short, actionable message
    - fix: optional, concrete fix instruction
    """

    level: str  # "ERROR" | "WARN"
    message: str
    fix: str | None = None


class AgentProvider(ABC):
    """
    Minimal provider interface. Implementations should be stateless.

    Providers may implement `preflight()` to validate configuration and environment
    before any persona executes (no network calls required).
    """

    def preflight(self, persona: Persona) -> list[PreflightIssue]:
        return []

    @abstractmethod
    def run(self, prompt: str, context_text: str, persona: Persona) -> str:
        raise NotImplementedError
