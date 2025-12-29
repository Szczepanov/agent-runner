from __future__ import annotations

from abc import ABC, abstractmethod
from agent_runner.personas.models import Persona


class AgentProvider(ABC):
    """
    Minimal provider interface. Implementations should be stateless.
    """

    @abstractmethod
    def run(self, prompt: str, context_text: str, persona: Persona) -> str:
        raise NotImplementedError
