from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any, Dict, List


@dataclass(frozen=True)
class Message:
    """Immutable value object representing a single message in a conversation."""

    content: str
    sender: str
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("Message content cannot be empty.")
        if not self.sender:
            raise ValueError("Message sender cannot be empty.")


class Agent(ABC):
    """Base abstract class for all agents in the system."""

    def __init__(self, name: str):
        self.name = name
        self._message_history: List[Message] = []

    @abstractmethod
    def process_message(self, message: Message) -> Message:
        """Process an incoming message and return a response."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the agent with any necessary setup."""

    @property
    def message_history(self) -> List[Message]:
        """Read-only view of the message history."""
        return list(self._message_history)

    def add_to_history(self, message: Message) -> None:
        self._message_history.append(message)

    def get_history(self) -> List[Message]:
        return list(self._message_history)
