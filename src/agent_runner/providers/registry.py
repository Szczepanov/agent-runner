from __future__ import annotations

from agent_runner.providers.base import AgentProvider
from agent_runner.providers.stub import StubProvider
from agent_runner.providers.jules import JulesProvider


def get_provider(name: str) -> AgentProvider:
    """
    Simple registry. Extend to support real providers.
    """
    if name in {"stub", "", None}:
        return StubProvider()
    if name == "jules":
        return JulesProvider()
    raise ValueError(f"Unknown provider: {name}")
