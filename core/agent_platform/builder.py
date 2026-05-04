import importlib
import pkgutil

import agents as _agents_package
from providers.base import LLMProvider
from core.coordinator import Coordinator
from core.agent_registry import get_definitions


def discover_agents() -> None:
    """Import all non-package modules in `agents/` to trigger @register_agent decorators.

    Safe to call multiple times - Python's module cache prevents re-execution.
    """
    for _finder, module_name, is_pkg in pkgutil.iter_modules(_agents_package.__path__):
        if not is_pkg:
            importlib.import_module(f"agents.{module_name}")


def build_agents(coordinator: Coordinator, provider: LLMProvider) -> None:
    """Discover, instantiate, initialize, and register all agents."""
    discover_agents()
    for definition in get_definitions():
        agent = definition.cls(definition.name, provider)
        agent.initialize()
        coordinator.add_agent(agent)
