"""OpenAI Realtime (voice) interview.

The browser connects directly to OpenAI over WebRTC using a short-lived
ephemeral token minted here — our real OPENAI_API_KEY never reaches the client.
The token is bound to a session pre-configured with THIS candidate's
profile-grounded interview instructions (built via the same PromptBuilder used
for the text flow), so the voice interviewer asks about their real work.

The candidate's spoken conversation is transcribed by OpenAI; the browser posts
the transcript back here so the existing evaluator can score it.
"""
from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import get_repository
from app.config import get_settings
from app.domain.enums import InterviewState
from app.domain.schemas import Turn
from app.domain.state_machine import InterviewStateMachine
from app.domain.strategies import get_strategy
from app.services.interview.prompt_builder import PromptBuilder

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

_OPENAI_CLIENT_SECRETS = "https://api.openai.com/v1/realtime/client_secrets"


def _build_instructions(session) -> str:
    strategy = get_strategy(session.config.seniority, session.config.interviewer_level)
    base = PromptBuilder().system_prompt(
        config=session.config,
        context=session.context,
        strategy=strategy,
        phase_directive=InterviewStateMachine.phase_directive(InterviewState.GREETING),
    )
    return (
        base
        + f"\n\nDELIVERY: This is a LIVE SPOKEN interview over voice. Speak naturally "
        f"and conversationally, one question at a time, and keep each turn short. "
        f"The interview lasts about {session.config.duration_minutes} minutes — pace "
        f"yourself, and when the time is nearly up, wrap up warmly and thank the "
        f"candidate. Begin now by greeting them and asking them to introduce themselves."
    )


@router.post("/token/{session_id}")
async def create_realtime_token(session_id: str):
    """Mint an ephemeral OpenAI Realtime token bound to this interview's config."""
    settings = get_settings()
    if not settings.has_openai:
        raise HTTPException(503, "OPENAI_API_KEY is not configured on the server.")

    repo = get_repository()
    session = repo.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")

    if session.started_ts is None:
        session.started_ts = time.time()
        session.deadline_ts = session.started_ts + session.config.duration_minutes * 60
        repo.save(session)

    body = {
        "expires_after": {"anchor": "created_at", "seconds": 3600},
        "session": {
            "type": "realtime",
            "model": settings.openai_realtime_model,
            "instructions": _build_instructions(session),
            "audio": {
                "input": {
                    "turn_detection": {"type": "server_vad"},
                    "transcription": {"model": "gpt-4o-transcribe"},
                },
                "output": {"voice": settings.openai_voice},
            },
        },
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            _OPENAI_CLIENT_SECRETS,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=body,
        )
    if resp.status_code >= 300:
        raise HTTPException(502, f"OpenAI token error: {resp.text[:300]}")

    data = resp.json()
    return {
        "token": data["client_secret"]["value"],
        "model": settings.openai_realtime_model,
        "deadline_ts": session.deadline_ts,
    }


class TranscriptTurn(BaseModel):
    role: str  # "interviewer" | "candidate"
    content: str


class TranscriptBody(BaseModel):
    turns: list[TranscriptTurn]


@router.post("/{session_id}/transcript")
def save_transcript(session_id: str, body: TranscriptBody):
    """Persist the voice-interview transcript so the evaluator can score it."""
    repo = get_repository()
    session = repo.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    session.transcript = [
        Turn(role="interviewer" if t.role == "interviewer" else "candidate", content=t.content)
        for t in body.turns
        if t.content.strip()
    ]
    repo.save(session)
    return {"status": "ok", "turns": len(session.transcript)}
