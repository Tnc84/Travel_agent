_RESPONSE_LEAK_MARKERS = ("System:", "User:", "Assistant:")


def clean_llm_response(response_text: str) -> str:
    """Strip residual prompt-leak markers (System:/User:/Assistant:) from LLM output."""
    if not response_text:
        return ""
    for marker in _RESPONSE_LEAK_MARKERS:
        if response_text.startswith(marker):
            parts = response_text.split("Assistant:", 1)
            if len(parts) > 1:
                return parts[-1].strip()
    return response_text.strip()
