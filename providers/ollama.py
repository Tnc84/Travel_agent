import logging
import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

from providers.base import LLMProvider
from core.utils import retry_on_error

load_dotenv()

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Provider that uses a local Ollama server."""

    def __init__(self, model: str, base_url: str = None):
        super().__init__(model)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._initialized = False

    @retry_on_error(max_retries=3, delay=1.0, exceptions=(requests.ConnectionError, requests.Timeout))
    def initialize(self) -> None:
        if self._initialized:
            return

        response = requests.get(f"{self.base_url}/api/tags", timeout=5)
        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama server is not available at {self.base_url}. "
                f"Status code: {response.status_code}"
            )
        self._initialized = True
        logger.info("Ollama provider initialized at %s using model %s", self.base_url, self.model)

    @retry_on_error(max_retries=3, delay=1.0, exceptions=(requests.ConnectionError, requests.Timeout))
    def _post_with_retry(self, url: str, **kwargs) -> requests.Response:
        return requests.post(url, **kwargs)

    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
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

            response = self._post_with_retry(
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

                logger.warning("Ollama API error %s: %s", response.status_code, error_detail)
                detail_str = f" ({error_detail})" if error_detail else ""
                return f"Sorry, I couldn't process your request. Ollama API error: {response.status_code}{detail_str}"

            response_json = response.json()
            content = response_json.get("message", {}).get("content")
            return content if content else str(response_json)

        except Exception as exc:
            logger.exception("Ollama request failed: %s", exc)
            return f"I apologize, but I encountered an error with Ollama: {exc}"
