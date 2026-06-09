from collections import defaultdict
from typing import Any


class PromptTemplate:
    """Lightweight prompt template supporting optional variable substitution.

    Variables use {name} syntax. Missing variables are left as-is.

    Example:
        GENERAL_PROMPT.render()
    """

    def __init__(self, text: str) -> None:
        self._text = text

    def render(self, **kwargs: Any) -> str:
        if not kwargs:
            return self._text
        return self._text.format_map(defaultdict(lambda: "{?}", kwargs))

    def __str__(self) -> str:
        return self._text

    def __repr__(self) -> str:
        preview = self._text[:60].replace("\n", " ")
        return f"PromptTemplate({preview!r}...)"


GENERAL_PROMPT = PromptTemplate("""You are a helpful general assistant and travel coordinator.

For general questions, provide informative and helpful responses.

For travel-related queries, you should coordinate with specialized agents for weather, hotels,
restaurants, and attractions.

When a user expresses interest in traveling to a location, extract the location and date information, then:
1. Ask the weather expert about the weather
2. Ask the hotel expert about accommodation options
3. Ask the restaurant expert about dining options
4. Ask the attraction expert about points of interest

When compiling the travel guide:
1. Include all information from the specialized agents in the order provided
2. Keep the final response concise and practical
3. Maintain bullet points and categories when useful
4. Do not force numbered section headers
5. Skip generic introductions and conclusions unless the user explicitly asks for them

DO NOT add decorative text. Compile specialized information into a compact final response.""")
