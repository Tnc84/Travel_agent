"""Application core packages (LangGraph travel runtime, agent platform, intent, etc.).

Import concrete subpackages explicitly to avoid import cycles, e.g.::

    from core.agent_platform import Coordinator, Message, register_agent
    from core.agent_platform.builder import build_agents

Barrel exports below are limited to symbols that do not eagerly load ``agents/``.
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
