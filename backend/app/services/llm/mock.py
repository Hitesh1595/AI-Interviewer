"""Offline mock provider so the UI runs without an OpenAI API key."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from app.services.llm.base import ChatMessage, LLMProvider


class MockProvider(LLMProvider):
    """Deterministic canned responses for local development/demo."""

    async def stream(
        self,
        *,
        system_instruction: str,
        contents: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        candidate_turns = [c for c in contents if c["role"] == "user"]
        if len(candidate_turns) <= 1:
            reply = (
                "Hi! I'm your AI interviewer today. We'll chat about your background "
                "and projects for a bit, then you can ask me anything. To start — "
                "could you tell me a little about yourself?"
            )
        else:
            reply = (
                "Thanks, that's helpful. Could you walk me through a project you're "
                "proud of and the specific technologies you used to build it?"
            )
        for word in reply.split(" "):
            yield word + " "

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.2,
    ) -> str:
        return json.dumps(
            {
                "dimension_scores": {
                    "technical_depth": 7,
                    "problem_solving": 7,
                    "communication": 8,
                    "experience_relevance": 6,
                    "behavioral": 7,
                },
                "strengths": [
                    "Communicates clearly",
                    "Shows genuine interest in the projects discussed",
                ],
                "weaknesses": ["Limited depth on system-level trade-offs"],
                "summary": (
                    "This is a mock evaluation generated because no OPENAI_API_KEY is "
                    "configured. Set your key to get real, transcript-based scoring."
                ),
                "recommendation": "yes",
            }
        )
