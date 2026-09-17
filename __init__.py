"""Serply web search provider plugin for Hermes Agent."""

from __future__ import annotations

from .provider import SerplyWebSearchProvider


def register(ctx) -> None:
    """Register the Serply provider with the Hermes plugin context."""
    ctx.register_web_search_provider(SerplyWebSearchProvider())
