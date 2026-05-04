from abc import ABC, abstractmethod
from typing import Dict, List


class LLMProvider(ABC):
    """Abstract base class for all LLM provider implementations."""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the provider and validate connectivity."""

    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate a response given a conversation history and a system prompt."""
