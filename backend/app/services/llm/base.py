"""LLM provider interface. Implementations are swappable via the factory."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypedDict


class ChatMessage(TypedDict):
    role: str  # "user" (candidate) or "model" (interviewer)
    text: str


class LLMProvider(ABC):
    @abstractmethod
    def stream(
        self,
        *,
        system_instruction: str,
        contents: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Yield reply text chunks for a multi-turn conversation."""
        raise NotImplementedError

    @abstractmethod
    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Return a raw JSON string response (application/json mode)."""
        raise NotImplementedError
