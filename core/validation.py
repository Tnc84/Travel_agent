_MAX_INPUT_LENGTH = 2_000
_MIN_INPUT_LENGTH = 1


def validate_user_input(text: str) -> str:
    """Validate and sanitize user input.

    Returns the stripped input if valid.
    Raises ValueError with a user-friendly message if not.
    """
    stripped = text.strip()

    if len(stripped) < _MIN_INPUT_LENGTH:
        raise ValueError("Input cannot be empty.")

    if len(stripped) > _MAX_INPUT_LENGTH:
        raise ValueError(
            f"Input is too long ({len(stripped)} chars). "
            f"Please keep it under {_MAX_INPUT_LENGTH} characters."
        )

    return stripped
