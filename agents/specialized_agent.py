from typing import Dict, List

from core.base import Agent, Message
from providers.base import LLMProvider

_DEFAULT_HISTORY_LIMIT = 5


class SpecializedAgent(Agent):
    """Base class for specialized agents that use LLM providers for domain-specific tasks."""

    def __init__(self, name: str, llm_provider: LLMProvider, history_limit: int = _DEFAULT_HISTORY_LIMIT):
        super().__init__(name)
        self.llm_provider = llm_provider
        self.system_prompt = f"You are {name}, a specialized AI assistant."
        self.specialization = ""
        self.history_limit = history_limit

    def initialize(self) -> None:
        self.llm_provider.initialize()

    def set_specialization(self, specialization: str) -> None:
        self.specialization = specialization

    def get_full_system_prompt(self) -> str:
        if self.specialization:
            return f"{self.system_prompt}\n\n{self.specialization}"
        return self.system_prompt

    def process_message(self, message: Message) -> Message:
        self.add_to_history(message)

        messages: List[Dict[str, str]] = []
        for msg in self._message_history[-self.history_limit:]:
            role = "assistant" if msg.sender == self.name else "user"
            messages.append({"role": role, "content": msg.content})

        if not messages or messages[-1]["content"] != message.content:
            messages.append({"role": "user", "content": message.content})

        response_text = self.llm_provider.generate_response(messages, self.get_full_system_prompt())

        response_message = Message(
            content=response_text,
            sender=self.name,
            metadata={"provider": self.llm_provider.__class__.__name__, "model": self.llm_provider.model},
        )
        self.add_to_history(response_message)
        return response_message
