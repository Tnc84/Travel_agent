from typing import Dict, Any, List
from core.base import Agent, Message
from agents.llm_provider import LLMProvider

class SpecializedAgent(Agent):
    """Base class for specialized agents that use LLM providers for domain-specific tasks."""
    
    def __init__(self, name: str, llm_provider: LLMProvider):
        super().__init__(name)
        self.llm_provider = llm_provider
        self.system_prompt = f"You are {name}, a specialized AI assistant."
        self.specialization = ""
        
    def initialize(self) -> None:
        """Initialize the agent with any necessary setup."""
        self.llm_provider.initialize()
    
    def set_specialization(self, specialization: str) -> None:
        """Set the agent's specialization to guide its responses."""
        self.specialization = specialization
    
    def get_full_system_prompt(self) -> str:
        """Get the full system prompt with specialization."""
        full_prompt = self.system_prompt
        if self.specialization:
            full_prompt += f"\n\n{self.specialization}"
        return full_prompt
    
    def process_message(self, message: Message) -> Message:
        """Process an incoming message and return a response using the LLM provider."""
        # Add the incoming message to history
        self.add_to_history(message)
        
        # Convert message history to format expected by LLM provider
        messages = []
        
        for msg in self.message_history[-5:]:  # Limit to last 5 messages
            role = "assistant" if msg.sender == self.name else "user"
            messages.append({"role": role, "content": msg.content})
        
        # Ensure the current message is included
        if len(messages) < 1 or messages[-1]["content"] != message.content:
            messages.append({"role": "user", "content": message.content})
        
        # Get full system prompt
        system_prompt = self.get_full_system_prompt()
        
        # Get response from LLM provider
        response_text = self.llm_provider.generate_response(messages, system_prompt)
        
        # Create response message
        response_message = Message(
            content=response_text,
            sender=self.name,
            metadata={"provider": self.llm_provider.__class__.__name__, "model": self.llm_provider.model}
        )
        
        # Add response to history
        self.add_to_history(response_message)
        
        return response_message 