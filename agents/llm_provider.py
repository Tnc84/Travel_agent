from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.base import Message

class LLMProvider(ABC):
    """Base class for LLM providers that handle the actual API calls to different language models."""
    
    def __init__(self, model: str):
        self.model = model
        
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the LLM provider with any necessary setup."""
        pass
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate a response from the LLM given a list of messages and a system prompt."""
        pass 