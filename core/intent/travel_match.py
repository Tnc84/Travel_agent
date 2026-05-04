import re
from typing import List, Optional, Tuple

_MONTHS = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?"
    r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r"|ian(?:uarie)?|feb(?:ruarie)?|mar(?:tie)?|apr(?:ilie)?|mai|iun(?:ie)?"
    r"|iul(?:ie)?|aug(?:ust)?|sep(?:tembrie)?|oct(?:ombrie)?|nov(?:embrie)?|dec(?:embrie)?)"
)

_TRAVEL_PATTERNS: List[re.Pattern] = [
    re.compile(
        r"(?:i want to|i'?d like to|i would like to|planning to|i'?m planning"
        r"|going to|traveling to|travelling to|flying to|heading to|visiting|visit|explore|discover|tour)\s+"
        r"(?:go to|visit|explore|discover|travel to|fly to|head to|see)?\s*"
        r"([a-zA-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\s]{1,40}?)\s+"
        r"(?:on|in|during|for|next|this)\s+([a-zA-Z0-9\s,./-]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:trip|travel|journey|vacation|holiday|getaway|tour|vacanta|calatorie)\s+(?:to|in|la|in)\s+"
        r"([a-zA-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\s]{1,40}?)\s+"
        r"(?:on|in|during|for|next|this|pe|in)\s+([a-zA-Z0-9\s,./-]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^([a-zA-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\s]{1,30}?)\s+"
        r"(\d{1,2}\s+" + _MONTHS + r"|" + _MONTHS + r"(?:\s+\d{1,2})?|\d{1,2}\s*[-/.]\s*\d{1,2})"
        r"\s*$",
        re.IGNORECASE,
    ),
]


def match_travel_intent(text: str) -> Optional[Tuple[str, str]]:
    """Return (location, date_str) if any travel pattern matches, else None."""
    for pattern in _TRAVEL_PATTERNS:
        match = pattern.search(text.strip())
        if match:
            location = match.group(1).strip().rstrip(",")
            date_str = match.group(2).strip().rstrip(".")
            if location and date_str:
                return location, date_str
    return None
