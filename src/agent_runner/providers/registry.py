from __future__ import annotations

from agent_runner.providers.base import AgentProvider
from agent_runner.providers.stub import StubProvider


def get_provider(name: str) -> AgentProvider:
    """
    Simple registry. Extend to support real providers.
    """
    if name in {"stub", "", None}:
        return StubProvider()
    raise ValueError(f"Unknown provider: {name}")
