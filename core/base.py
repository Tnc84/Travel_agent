from abc import ABC, abstractmethod
from typing import Any, Dict, List

class Message:
    def __init__(self, content: str, sender: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.sender = sender
        self.metadata = metadata or {}

class Agent(ABC):
    """Base abstract class for all agents in the system."""
    
    def __init__(self, name: str):
        self.name = name
        self.message_history: List[Message] = []
    
    @abstractmethod
    def process_message(self, message: Message) -> Message:
        """Process an incoming message and return a response."""
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the agent with any necessary setup."""
        pass
    
    def add_to_history(self, message: Message) -> None:
        """Add a message to the agent's history."""
        self.message_history.append(message)
    
    def get_history(self) -> List[Message]:
        """Get the agent's message history."""
        return self.message_history 