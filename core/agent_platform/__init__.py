"""Multi-agent orchestration layer (distinct from top-level package ``agents``).

Heavy imports (``build_agents``, ``discover_agents``) live in ``builder`` and are
not re-exported from this package root to avoid import cycles with ``agents/``.
Import explicitly::

    from core.agent_platform.builder import build_agents
"""
from core.agent_platform.base import Agent, Message
from core.agent_platform.coordinator import Coordinator
from core.agent_platform.registry import AgentDefinition, get_definitions, register_agent

__all__ = [
    "Agent",
    "AgentDefinition",
    "Coordinator",
    "Message",
    "get_definitions",
    "register_agent",
]
