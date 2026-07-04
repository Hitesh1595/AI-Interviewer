"""Claude (Anthropic) implementation of LLMProvider using the async SDK.

Notes on Opus 4.8 / 4.7:
- `temperature` / `top_p` / `top_k` are removed (400 if sent) — we never pass them.
- Thinking is off when the `thinking` field is omitted; we omit it for low-latency
  conversational replies and use `output_config.effort` to tune depth/cost.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from app.services.llm.base import ChatMessage, LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @staticmethod
    def _to_messages(contents: list[ChatMessage]) -> list[dict]:
        # Our internal "model" role maps to Anthropic's "assistant".
        return [
            {"role": "assistant" if m["role"] == "model" else "user", "content": m["text"]}
            for m in contents
        ]

    async def stream(
        self,
        *,
        system_instruction: str,
        contents: list[ChatMessage],
        temperature: float = 0.7,  # ignored on Opus 4.8/4.7
    ) -> AsyncIterator[str]:
        # Note: no `effort` param — it 400s on Haiku 4.5. Thinking is omitted
        # (off by default), which keeps conversational turns fast.
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=1024,
            system=system_instruction,
            messages=self._to_messages(contents),
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.2,
    ) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_instruction,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text") or "{}"
