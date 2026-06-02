import logging
import time
from functools import wraps
from typing import Callable, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)

_DEFAULT_RETRIES = 3
_DEFAULT_DELAY = 1.0
_DEFAULT_BACKOFF = 2.0


def retry_on_error(
    max_retries: int = _DEFAULT_RETRIES,
    delay: float = _DEFAULT_DELAY,
    backoff: float = _DEFAULT_BACKOFF,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry a function on specified exceptions with exponential backoff.

    Args:
        max_retries: total number of attempts (including first).
        delay: initial sleep between retries in seconds.
        backoff: multiplier applied to delay on each retry.
        exceptions: exception types that trigger a retry.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception = RuntimeError("No attempts made.")
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        sleep_time = delay * (backoff ** attempt)
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs...",
                            func.__qualname__,
                            attempt + 1,
                            max_retries,
                            exc,
                            sleep_time,
                        )
                        time.sleep(sleep_time)
            raise last_exc

        return wrapper  # type: ignore[return-value]

    return decorator
