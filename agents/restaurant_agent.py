from agents.specialized_agent import SpecializedAgent
from agents.prompts import RESTAURANT_PROMPT
from core.agent_registry import register_agent
from providers.base import LLMProvider


@register_agent(
    name="RestaurantExpert",
    keywords=["restaurant", "food", "eat", "dining", "cuisine", "meal", "breakfast", "lunch", "dinner"],
)
class RestaurantAgent(SpecializedAgent):
    """An agent that specializes in finding the best restaurants in a location."""

    def __init__(self, name: str = "RestaurantExpert", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a restaurant specialist AI assistant."

    def initialize(self) -> None:
        super().initialize()
        if not self.specialization:
            self.set_specialization(RESTAURANT_PROMPT.render())
