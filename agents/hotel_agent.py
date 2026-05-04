from agents.specialized_agent import SpecializedAgent
from agents.prompts import HOTEL_PROMPT
from core.agent_platform import register_agent
from llm_providers.base import LLMProvider


@register_agent(
    name="HotelExpert",
    keywords=["hotel", "motel", "accommodation", "stay", "room", "suite", "lodge", "resort"],
)
class HotelAgent(SpecializedAgent):
    """An agent that specializes in finding the best hotels in a location."""

    def __init__(self, name: str = "HotelExpert", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a hotel specialist AI assistant."

    def initialize(self) -> None:
        super().initialize()
        if not self.specialization:
            self.set_specialization(HOTEL_PROMPT.render())
