from agents.specialized_agent import SpecializedAgent
from agents.prompts import ATTRACTION_PROMPT
from core.agent_platform import register_agent
from llm_providers.base import LLMProvider


@register_agent(
    name="AttractionExpert",
    keywords=["attraction", "visit", "sightseeing", "tour", "museum", "landmark", "monument", "park", "gallery"],
)
class AttractionAgent(SpecializedAgent):
    """An agent that specializes in finding the best tourist attractions in a location."""

    def __init__(self, name: str = "AttractionExpert", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a tourist attraction specialist AI assistant."

    def initialize(self) -> None:
        super().initialize()
        if not self.specialization:
            self.set_specialization(ATTRACTION_PROMPT.render())
