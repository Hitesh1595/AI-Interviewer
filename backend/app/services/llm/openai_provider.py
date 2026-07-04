"""OpenAI text implementation of LLMProvider (used for evaluation scoring).

Uses the Chat Completions REST API via httpx (no extra SDK dependency). The
live voice conversation is handled separately by the Realtime API (WebRTC);
this provider powers the transcript evaluation and any text fallback.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.services.llm.base import ChatMessage, LLMProvider

_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _to_messages(system: str, contents: list[ChatMessage]) -> list[dict]:
        msgs = [{"role": "system", "content": system}]
        for m in contents:
            msgs.append(
                {"role": "assistant" if m["role"] == "model" else "user", "content": m["text"]}
            )
        return msgs

    async def stream(
        self,
        *,
        system_instruction: str,
        contents: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": self._to_messages(system_instruction, contents),
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", _CHAT_URL, headers=self._headers(), json=payload) as r:
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"].get("content")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if delta:
                        yield delta

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.2,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(_CHAT_URL, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"] or "{}"
