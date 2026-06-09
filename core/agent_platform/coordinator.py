from typing import Dict

from core.agent_platform.base import Agent, Message


class Coordinator:
    """Manages routing of messages between registered agents."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    def process_message(self, message: Message, target_agent: str) -> Message:
        if target_agent not in self.agents:
            raise ValueError(f"Agent '{target_agent}' not found. Available: {list(self.agents.keys())}")
        return self.agents[target_agent].process_message(message)
