import json
import logging
import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

from providers.base import LLMProvider
from core.utils import retry_on_error

load_dotenv()

logger = logging.getLogger(__name__)


class HuggingFaceProvider(LLMProvider):
    """Provider that uses HuggingFace's Inference API to generate responses."""

    def __init__(self, model_id: str = "HuggingFaceH4/zephyr-7b-beta"):
        super().__init__(model_id)
        self.model_id = model_id
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    def initialize(self) -> None:
        if not self.api_key:
            logger.info("No HUGGINGFACE_API_KEY provided. Using free tier with rate limits.")

    @retry_on_error(max_retries=3, delay=1.0, exceptions=(requests.ConnectionError, requests.Timeout))
    def _post_with_retry(self, url: str, **kwargs) -> requests.Response:
        return requests.post(url, **kwargs)

    @staticmethod
    def _extract_assistant_reply(text: str) -> str:
        """Return only the last assistant turn from a full prompt+response string."""
        marker = "Assistant: "
        if marker in text:
            return text.split(marker)[-1].strip()
        return text.strip()

    def generate_response(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        try:
            prompt = ""
            if system_prompt:
                prompt += f"System: {system_prompt}\n\n"

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt += f"User: {content}\n"
                elif role == "assistant":
                    prompt += f"Assistant: {content}\n"

            prompt += "Assistant: "

            logger.debug("Formatted prompt (first 200 chars): %s", prompt[:200])

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {"inputs": prompt}

            logger.debug("Sending request to HuggingFace API for model %s", self.model_id)

            response = self._post_with_retry(self.api_url, headers=headers, json=payload, timeout=120)

            logger.debug("Response status: %s", response.status_code)

            if response.status_code == 200:
                response_json = response.json()

                raw = None
                if isinstance(response_json, list) and response_json:
                    item = response_json[0]
                    raw = item.get("generated_text") if isinstance(item, dict) else item
                elif isinstance(response_json, dict):
                    raw = response_json.get("generated_text")
                elif isinstance(response_json, str):
                    raw = response_json

                if raw is None:
                    return str(response_json)

                return self._extract_assistant_reply(str(raw))

            error_message = f"Sorry, I couldn't process your request. API error: {response.status_code}"
            try:
                error_data = response.json()
                if "estimated_time" in response.text:
                    wait_time = error_data.get("estimated_time", "unknown")
                    return (
                        f"The model is still loading and will be ready in approximately "
                        f"{wait_time} seconds. Please try again shortly."
                    )
                logger.warning("HuggingFace API error %s: %s", response.status_code, json.dumps(error_data))
            except Exception:
                logger.warning("HuggingFace API error %s: %s", response.status_code, response.text)

            return error_message

        except Exception as exc:
            logger.exception("HuggingFace request failed: %s", exc)
            return f"I apologize, but I encountered an error when trying to process your query: {exc}"
