from typing import Dict, List, Optional

from core.base import Agent, Message

_DEFAULT_HISTORY_LIMIT = 200


class Coordinator:
    """Manages communication between multiple agents."""

    def __init__(self, history_limit: int = _DEFAULT_HISTORY_LIMIT):
        self.agents: Dict[str, Agent] = {}
        self._history: List[Message] = []
        self.history_limit = history_limit

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    def remove_agent(self, agent_name: str) -> None:
        self.agents.pop(agent_name, None)

    def get_agent(self, agent_name: str) -> Optional[Agent]:
        return self.agents.get(agent_name)

    def process_message(self, message: Message, target_agent: str) -> Message:
        if target_agent not in self.agents:
            raise ValueError(f"Agent '{target_agent}' not found. Available: {list(self.agents.keys())}")

        self._append_history(message)
        response = self.agents[target_agent].process_message(message)
        self._append_history(response)
        return response

    def get_history(self) -> List[Message]:
        return list(self._history)

    def _append_history(self, message: Message) -> None:
        self._history.append(message)
        if len(self._history) > self.history_limit:
            self._history = self._history[-self.history_limit:]
