from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

_REGISTRY: Dict[str, "AgentDefinition"] = {}


@dataclass
class AgentDefinition:
    """Metadata for a registered agent."""

    name: str
    cls: Type
    keywords: List[str] = field(default_factory=list)


def register_agent(name: str, keywords: Optional[List[str]] = None):
    """Class decorator that registers an agent in the global registry.

    Usage:
        @register_agent(name="WeatherExpert", keywords=["weather", "forecast"])
        class WeatherAgent(SpecializedAgent):
            ...

    To add a new agent: create its class file and apply this decorator.
    No other file needs to be modified.
    """
    def decorator(cls: Type) -> Type:
        _REGISTRY[name] = AgentDefinition(name=name, cls=cls, keywords=keywords or [])
        return cls

    return decorator


def get_definitions() -> List[AgentDefinition]:
    """Return all registered agent definitions."""
    return list(_REGISTRY.values())
