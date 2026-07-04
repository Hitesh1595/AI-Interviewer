"""Factory pattern: pick the LLM provider based on configuration.

LLM_PROVIDER controls the choice: "gemini" | "anthropic" | "mock" | "auto".
"auto" prefers whichever key is configured (Anthropic first, then Gemini),
falling back to the offline mock so the UI always runs.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import LLMProvider
from app.services.llm.gemini import GeminiProvider
from app.services.llm.mock import MockProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    provider = (s.llm_provider or "gemini").lower()

    if provider == "mock":
        return MockProvider()
    if provider == "anthropic" and s.has_anthropic:
        return AnthropicProvider(s.anthropic_api_key, s.anthropic_model)
    if provider == "gemini" and s.has_gemini:
        return GeminiProvider(s.gemini_api_key, s.gemini_model)

    # auto / fallback
    if s.has_anthropic:
        return AnthropicProvider(s.anthropic_api_key, s.anthropic_model)
    if s.has_gemini:
        return GeminiProvider(s.gemini_api_key, s.gemini_model)
    return MockProvider()


def active_provider_name() -> str:
    p = get_llm_provider()
    return type(p).__name__.replace("Provider", "").lower()
