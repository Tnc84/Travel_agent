from agents.specialized_agent import SpecializedAgent
from agents.prompts import WEATHER_PROMPT
from core.agent_platform import register_agent
from llm_providers.base import LLMProvider


@register_agent(
    name="WeatherExpert",
    keywords=["weather", "temperature", "forecast", "rain", "sunny", "climate", "humid", "cold", "hot"],
)
class WeatherAgent(SpecializedAgent):
    """An agent that specializes in providing weather information for locations."""

    def __init__(self, name: str = "WeatherExpert", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a weather specialist AI assistant."

    def initialize(self) -> None:
        super().initialize()
        if not self.specialization:
            self.set_specialization(WEATHER_PROMPT.render())
