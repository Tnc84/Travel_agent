from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

from core.graph.config import GraphConfigError, GraphRuntimeConfig

logger = logging.getLogger(__name__)


@contextmanager
def open_checkpointer(config: GraphRuntimeConfig) -> Iterator[BaseCheckpointSaver]:
    """Open the appropriate checkpoint saver based on runtime config.

    Yields a `BaseCheckpointSaver`. Tables are auto-created via `setup()` for Postgres.
    For degraded startup (no DSN, allow_no_checkpoint=1), an in-memory saver is used.
    """
    if config.checkpoint_dsn:
        with PostgresSaver.from_conn_string(config.checkpoint_dsn) as saver:
            try:
                saver.setup()
            except Exception as exc:
                logger.exception("Postgres checkpoint setup failed: %s", exc)
                if not config.allow_no_checkpoint:
                    raise GraphConfigError(
                        f"Failed to initialize Postgres checkpoint store: {exc}"
                    ) from exc
                logger.warning("Falling back to in-memory checkpointer (degraded mode)")
                yield InMemorySaver()
                return
            logger.info("Postgres checkpointer ready (durable graph state enabled)")
            yield saver
        return

    if not config.allow_no_checkpoint:
        raise GraphConfigError(
            "LANGGRAPH_CHECKPOINT_DSN missing and LANGGRAPH_ALLOW_NO_CHECKPOINT not set."
        )
    logger.warning(
        "Starting LangGraph runtime with in-memory checkpointer (LANGGRAPH_ALLOW_NO_CHECKPOINT=1)"
    )
    yield InMemorySaver()
