"""Gemini implementation of LLMProvider using the async google-genai client."""
from __future__ import annotations

from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.services.llm.base import ChatMessage, LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @staticmethod
    def _to_contents(contents: list[ChatMessage]) -> list[types.Content]:
        return [
            types.Content(role=m["role"], parts=[types.Part(text=m["text"])])
            for m in contents
        ]

    async def stream(
        self,
        *,
        system_instruction: str,
        contents: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            # Disable "thinking" for low-latency conversational replies (2.5 models).
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        stream = await self._client.aio.models.generate_content_stream(
            model=self._model,
            contents=self._to_contents(contents),
            config=config,
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.2,
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=config,
        )
        return response.text or "{}"
