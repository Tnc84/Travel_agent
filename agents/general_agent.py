from agents.specialized_agent import SpecializedAgent
from agents.prompts import GENERAL_PROMPT
from core.agent_registry import register_agent
from providers.base import LLMProvider


@register_agent(name="Assistant")
class GeneralAgent(SpecializedAgent):
    """A general-purpose assistant agent that can coordinate with specialized agents."""

    def __init__(self, name: str = "Assistant", llm_provider: LLMProvider = None):
        super().__init__(name, llm_provider)
        self.system_prompt = f"You are {name}, a helpful AI assistant."

    def initialize(self) -> None:
        super().initialize()
        if not self.specialization:
            self.set_specialization(GENERAL_PROMPT.render())
