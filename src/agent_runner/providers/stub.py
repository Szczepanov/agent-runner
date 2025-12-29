from __future__ import annotations

from agent_runner.providers.base import AgentProvider
from agent_runner.personas.models import Persona


class StubProvider(AgentProvider):
    """
    Placeholder provider for repo skeleton.
    Replace with real providers (Jules/OpenAI/etc.).
    """

    def run(self, prompt: str, context_text: str, persona: Persona) -> str:
        return (
            f"# {persona.display_name or persona.name}\n\n"
            "## NOTE\n"
            "This is the stub provider output. Configure a real provider to produce actual findings.\n\n"
            "## Prompt (truncated)\n"
            f"{prompt[:800]}\n\n"
            "## Context\n"
            f"{context_text}\n"
        )
