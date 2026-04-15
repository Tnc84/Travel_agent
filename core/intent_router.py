import re
from typing import List, Optional, Tuple

from core.agent_registry import get_definitions

_DEFAULT_AGENT = "Assistant"

_TRAVEL_PATTERNS: List[re.Pattern] = [
    # "I want to go to Paris on July 4th" / "I'd like to visit London in December"
    re.compile(
        r"(?:i want to|i'd like to|i would like to|planning to|i'm planning)\s+"
        r"(?:go to|visit|travel to|fly to|head to|explore|see)?\s*"
        r"([a-zA-Z][a-zA-Z\s]{1,40}?)\s+"
        r"(?:on|in|during|for|next|this)\s+([a-zA-Z0-9\s,]+)",
        re.IGNORECASE,
    ),
    # "going to / traveling to Paris in July"
    re.compile(
        r"(?:going to|traveling to|travelling to|flying to|heading to|visiting)\s+"
        r"([a-zA-Z][a-zA-Z\s]{1,40}?)\s+"
        r"(?:on|in|during|for|next|this)\s+([a-zA-Z0-9\s,]+)",
        re.IGNORECASE,
    ),
    # "trip/vacation/holiday to Paris in July"
    re.compile(
        r"(?:trip|travel|journey|vacation|holiday|getaway|tour)\s+(?:to|in)\s+"
        r"([a-zA-Z][a-zA-Z\s]{1,40}?)\s+"
        r"(?:on|in|during|for|next|this)\s+([a-zA-Z0-9\s,]+)",
        re.IGNORECASE,
    ),
    # "visit/explore Paris in July"
    re.compile(
        r"(?:visit|explore|discover|tour)\s+"
        r"([a-zA-Z][a-zA-Z\s]{1,40}?)\s+"
        r"(?:on|in|during|for|next|this)\s+([a-zA-Z0-9\s,]+)",
        re.IGNORECASE,
    ),
]


def match_travel_intent(text: str) -> Optional[Tuple[str, str]]:
    """Return (location, date_str) if any travel pattern matches, else None."""
    for pattern in _TRAVEL_PATTERNS:
        match = pattern.search(text)
        if match:
            location = match.group(1).strip().rstrip(",")
            date_str = match.group(2).strip().rstrip(".")
            if location and date_str:
                return location, date_str
    return None


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
