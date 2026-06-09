from __future__ import annotations

import logging
from dataclasses import dataclass

from core.agent_platform import Coordinator
from core.graph.runner import TravelGraphRunner


@dataclass(frozen=True)
class AppContext:
    """Runtime dependencies injected into HTTP handlers (DIP)."""

    coordinator: Coordinator
    runner: TravelGraphRunner
    logger: logging.Logger
