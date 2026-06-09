from __future__ import annotations

import atexit
import logging
import os

from dotenv import load_dotenv

from core.agent_platform import Coordinator
from core.agent_platform.builder import build_agents
from core.graph.runner import TravelGraphRunner
from core.location import LocationResolver
from core.llm import build_primary_provider
from ui.context import AppContext


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        filename="travel_agent.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("travel_agent")


def _build_coordinator(logger: logging.Logger) -> Coordinator:
    load_dotenv()

    huggingface_key = os.getenv("HUGGINGFACE_API_KEY")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    logger.info("Ollama endpoint: %s", ollama_base_url)
    logger.info(
        "Hugging Face API: %s",
        "✓ (API key provided)" if huggingface_key else "✓ (free tier)",
    )

    primary_provider_name, primary_provider = build_primary_provider(logger.warning)
    logger.info("Using %s as primary provider", primary_provider_name)

    coordinator = Coordinator()
    build_agents(coordinator, primary_provider)
    return coordinator


def _start_runner(coordinator: Coordinator, logger: logging.Logger) -> TravelGraphRunner:
    location_resolver = LocationResolver()
    runner = TravelGraphRunner(coordinator, location_resolver)
    runner.__enter__()
    logger.info(
        "LangGraph travel runtime started (checkpoint=%s)",
        bool(runner.config.checkpoint_dsn),
    )
    atexit.register(lambda: runner.__exit__(None, None, None))
    return runner


def build_app_context() -> AppContext:
    logger = configure_logging()
    coordinator = _build_coordinator(logger)
    runner = _start_runner(coordinator, logger)
    return AppContext(coordinator=coordinator, runner=runner, logger=logger)
