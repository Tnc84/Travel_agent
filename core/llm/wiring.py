import os
from typing import Callable, Optional, Tuple

from llm_providers.base import LLMProvider
from llm_providers.huggingface import HuggingFaceProvider
from llm_providers.ollama import OllamaProvider


def build_primary_provider(
    log_warning: Optional[Callable[[str], None]] = None,
) -> Tuple[str, LLMProvider]:
    """Build a primary provider with fallback based on environment configuration."""
    preferred_provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    ollama_model = os.getenv("OLLAMA_MODEL", "ministral-3:3b")
    huggingface_model = os.getenv("HUGGINGFACE_MODEL", "HuggingFaceH4/zephyr-7b-beta")

    if preferred_provider not in {"ollama", "huggingface"}:
        warning = f"Unknown LLM_PROVIDER '{preferred_provider}', defaulting to 'ollama'"
        if log_warning:
            log_warning(warning)
        preferred_provider = "ollama"

    if preferred_provider == "huggingface":
        candidates = [
            ("huggingface", HuggingFaceProvider(huggingface_model)),
            ("ollama", OllamaProvider(ollama_model)),
        ]
    else:
        candidates = [
            ("ollama", OllamaProvider(ollama_model)),
            ("huggingface", HuggingFaceProvider(huggingface_model)),
        ]

    last_error = None
    for provider_name, provider in candidates:
        try:
            provider.initialize()
            return provider_name, provider
        except Exception as exc:
            last_error = exc
            warning = f"Provider '{provider_name}' unavailable: {exc}"
            if log_warning:
                log_warning(warning)
            else:
                print(warning)

    raise RuntimeError(f"No LLM provider available. Last error: {last_error}")
