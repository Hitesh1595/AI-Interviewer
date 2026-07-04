"""WebSocket handler driving the live interview conversation.

Protocol (JSON messages):
  server -> client:  {type:"state", state, started_ts, deadline_ts}
                     {type:"interviewer_token", token}
                     {type:"done"}                      (interviewer message complete)
                     {type:"evaluation_ready", evaluation}
                     {type:"error", detail}
  client -> server:  {type:"candidate_msg", content}
                     {type:"finish"}
"""
from __future__ import annotations

import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_engine, get_evaluator, get_repository
from app.domain.enums import InterviewState
from app.domain.schemas import InterviewSession, Turn
from app.domain.state_machine import InterviewStateMachine
from app.domain.strategies import get_strategy

router = APIRouter()


def friendly_llm_error(exc: Exception) -> str:
    s = str(exc)
    if "429" in s or "rate" in s.lower() or "quota" in s.lower():
        return "The AI model hit its rate/quota limit. Please wait a moment and retry."
    if "API key" in s or "401" in s or "403" in s:
        return "The OpenAI API key is missing or invalid. Set OPENAI_API_KEY and restart."
    return f"AI model error: {s[:200]}"


async def _stream_interviewer(ws: WebSocket, session: InterviewSession) -> str | None:
    """Stream one interviewer turn to the client; return the full text or None on error."""
    engine = get_engine()
    buffer: list[str] = []
    try:
        async for token in engine.stream_interviewer_turn(session):
            buffer.append(token)
            await ws.send_json({"type": "interviewer_token", "token": token})
    except Exception as exc:  # LLM/network failure — keep the socket alive.
        await ws.send_json({"type": "error", "detail": friendly_llm_error(exc)})
        return None
    text = "".join(buffer).strip()
    if not text:
        await ws.send_json({"type": "error", "detail": "The interviewer returned no response — please retry."})
        return None
    session.transcript.append(Turn(role="interviewer", content=text))
    await ws.send_json({"type": "done"})
    return text


@router.websocket("/api/ws/interview/{session_id}")
async def interview_ws(ws: WebSocket, session_id: str) -> None:
    await ws.accept()
    repo = get_repository()
    session = repo.get(session_id)
    if session is None:
        await ws.send_json({"type": "error", "detail": "session not found"})
        await ws.close()
        return

    # Already evaluated -> hand back the result immediately.
    if session.evaluation is not None:
        await ws.send_json(
            {"type": "evaluation_ready", "evaluation": session.evaluation.model_dump(mode="json")}
        )
        await ws.close()
        return

    # Start the clock on first connect.
    if session.started_ts is None:
        session.started_ts = time.time()
        session.deadline_ts = session.started_ts + session.config.duration_minutes * 60
        repo.save(session)

    await ws.send_json(
        {
            "type": "state",
            "state": session.state.value,
            "started_ts": session.started_ts,
            "deadline_ts": session.deadline_ts,
        }
    )

    # Replay any existing transcript so refresh/reconnect renders prior turns.
    await ws.send_json(
        {
            "type": "history",
            "turns": [t.model_dump(mode="json") for t in session.transcript],
        }
    )

    strategy = get_strategy(session.config.seniority, session.config.interviewer_level)
    sm = InterviewStateMachine(strategy.question_budget)

    try:
        # Interviewer opens with a self-introduction if the transcript is empty.
        if not session.transcript:
            await _stream_interviewer(ws, session)
            repo.save(session)

        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "finish":
                session.finish_requested = True
            elif mtype == "candidate_msg":
                content = (msg.get("content") or "").strip()
                if not content:
                    continue
                session.transcript.append(Turn(role="candidate", content=content))
            else:
                continue

            # Decide the next state from the (updated) observable session state.
            next_state = sm.decide(
                state=session.state,
                elapsed_fraction=session.elapsed_fraction(),
                interviewer_turns=session.interviewer_turns,
                finish_requested=session.finish_requested,
            )
            session.state = next_state

            if next_state == InterviewState.EVALUATION:
                try:
                    session.evaluation = await get_evaluator().evaluate(session)
                except Exception as exc:
                    # Keep the socket open so the user can retry finishing.
                    session.state = InterviewState.WRAP_UP
                    repo.save(session)
                    await ws.send_json({"type": "error", "detail": friendly_llm_error(exc)})
                    continue
                session.state = InterviewState.COMPLETE
                repo.save(session)
                await ws.send_json(
                    {
                        "type": "evaluation_ready",
                        "evaluation": session.evaluation.model_dump(mode="json"),
                    }
                )
                await ws.close()
                return

            await ws.send_json({"type": "state", "state": session.state.value})
            await _stream_interviewer(ws, session)
            repo.save(session)

    except WebSocketDisconnect:
        # Persist whatever we have; the client's timer/finish will evaluate later.
        repo.save(session)
