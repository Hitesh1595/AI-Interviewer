"""Factory pattern: pick the LLM provider.

The project runs on OpenAI (text evaluation + Realtime voice). When no key is
configured it falls back to an offline mock so the UI still runs.
LLM_PROVIDER: "openai" | "mock" | "auto".
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock import MockProvider
from app.services.llm.openai_provider import OpenAIProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    provider = (s.llm_provider or "openai").lower()

    if provider == "mock":
        return MockProvider()
    if s.has_openai:  # "openai" or "auto"
        return OpenAIProvider(s.openai_api_key, s.openai_text_model)
    return MockProvider()


def active_provider_name() -> str:
    return type(get_llm_provider()).__name__.replace("Provider", "").lower()
