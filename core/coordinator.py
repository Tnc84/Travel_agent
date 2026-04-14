from typing import Dict, List
from core.base import Agent, Message

class Coordinator:
    """Manages communication between multiple agents."""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.history: List[Message] = []
    
    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the coordinator."""
        self.agents[agent.name] = agent
    
    def remove_agent(self, agent_name: str) -> None:
        """Remove an agent from the coordinator."""
        if agent_name in self.agents:
            del self.agents[agent_name]
    
    def get_agent(self, agent_name: str) -> Agent:
        """Get an agent by name."""
        return self.agents.get(agent_name)
    
    def process_message(self, message: Message, target_agent: str) -> Message:
        """Process a message using the specified agent."""
        if target_agent not in self.agents:
            raise ValueError(f"Agent '{target_agent}' not found")
        
        # Add message to history
        self.history.append(message)
        
        # Process message with target agent
        agent = self.agents[target_agent]
        response = agent.process_message(message)
        
        # Add response to history
        self.history.append(response)
        
        return response
    
    def get_history(self) -> List[Message]:
        """Get the full message history."""
        return self.history 