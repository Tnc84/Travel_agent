"""LLM provider wiring from environment (selection + fallback)."""

from core.llm.wiring import build_primary_provider

__all__ = ["build_primary_provider"]
