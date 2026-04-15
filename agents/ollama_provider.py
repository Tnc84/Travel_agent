import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

from agents.llm_provider import LLMProvider

load_dotenv()


class OllamaProvider(LLMProvider):
    """Provider that uses a local Ollama server."""

    def __init__(self, model: str, base_url: str = None):
        super().__init__(model)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._initialized = False

    def initialize(self) -> None:
        """Initialize and validate Ollama connectivity."""
        if self._initialized:
            return

        response = requests.get(f"{self.base_url}/api/tags", timeout=5)
        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama server is not available at {self.base_url}. "
                f"Status code: {response.status_code}"
            )
        self._initialized = True

    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate a response using Ollama chat API."""
        try:
            chat_messages = []
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})

            chat_messages.extend(messages)

            payload = {
                "model": self.model,
                "messages": chat_messages,
                "stream": False,
            }

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            )

            if response.status_code != 200:
                error_detail = ""
                try:
                    error_payload = response.json()
                    error_detail = error_payload.get("error") or str(error_payload)
                except Exception:
                    error_detail = response.text.strip()

                if error_detail:
                    return (
                        "Sorry, I couldn't process your request. "
                        f"Ollama API error: {response.status_code} ({error_detail})"
                    )
                return f"Sorry, I couldn't process your request. Ollama API error: {response.status_code}"

            response_json = response.json()
            message = response_json.get("message", {})
            content = message.get("content")

            if content:
                return content

            return str(response_json)
        except Exception as exc:
            return f"I apologize, but I encountered an error with Ollama: {str(exc)}"
