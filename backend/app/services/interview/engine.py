"""Interview engine: orchestrates one interviewer turn at a time.

Stateless with respect to storage — it operates on an `InterviewSession` passed
in, streams the next interviewer message from the LLM, and lets the caller
(the WebSocket handler) persist the mutated session.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.domain.schemas import InterviewSession
from app.domain.state_machine import InterviewStateMachine
from app.domain.strategies import get_strategy
from app.services.interview.prompt_builder import PromptBuilder
from app.services.llm.base import ChatMessage, LLMProvider

# Bootstrap message used to kick off the very first interviewer turn.
_KICKOFF = "Please begin the interview now."


class InterviewEngine:
    def __init__(self, llm: LLMProvider, prompt_builder: PromptBuilder) -> None:
        self._llm = llm
        self._prompt_builder = prompt_builder

    @staticmethod
    def _to_contents(session: InterviewSession) -> list[ChatMessage]:
        contents: list[ChatMessage] = [
            {
                "role": "model" if t.role == "interviewer" else "user",
                "text": t.content,
            }
            for t in session.transcript
        ]
        # The Gemini API needs a trailing user turn to respond to. If the last
        # turn was the interviewer (or the transcript is empty), append a kickoff.
        if not contents or contents[-1]["role"] == "model":
            contents.append({"role": "user", "text": _KICKOFF})
        return contents

    async def stream_interviewer_turn(
        self, session: InterviewSession
    ) -> AsyncIterator[str]:
        strategy = get_strategy(
            session.config.seniority, session.config.interviewer_level
        )
        directive = InterviewStateMachine.phase_directive(session.state)
        system_prompt = self._prompt_builder.system_prompt(
            config=session.config,
            context=session.context,
            strategy=strategy,
            phase_directive=directive,
        )
        async for chunk in self._llm.stream(
            system_instruction=system_prompt,
            contents=self._to_contents(session),
        ):
            yield chunk
