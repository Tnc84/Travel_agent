from core.agent_platform import get_definitions

_DEFAULT_AGENT = "Assistant"


def route_by_keywords(text: str, current_agent: str = _DEFAULT_AGENT) -> str:
    """Return the best matching agent name based on keywords in the text.

    Only routes away from the default agent; specialists keep their assignment.
    Keywords are sourced from the agent registry populated by @register_agent.
    """
    if current_agent != _DEFAULT_AGENT:
        return current_agent

    text_lower = text.lower()
    for definition in get_definitions():
        if definition.keywords and any(kw in text_lower for kw in definition.keywords):
            return definition.name

    return _DEFAULT_AGENT
