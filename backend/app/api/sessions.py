"""REST endpoints: create session, fetch state, finish, and get results."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.auth import require_admin
from app.api.deps import get_evaluator, get_repository
from app.domain.enums import InterviewerLevel, InterviewState, Seniority
from app.domain.schemas import Feedback, InterviewConfig, InterviewSession
from app.services.intake import build_candidate_context, read_pdf

router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions", dependencies=[Depends(require_admin)])
async def create_session(
    role_title: str = Form(...),
    seniority: Seniority = Form(...),
    interviewer_level: InterviewerLevel = Form(InterviewerLevel.BALANCED),
    duration_minutes: int = Form(15),
    focus_areas: str = Form(""),
    github_url: str = Form(""),
    linkedin_text: str = Form(""),
    linkedin_pdf: UploadFile | None = File(None),
    resume_pdf: UploadFile | None = File(None),
):
    """Direct single-step flow (admin builds config + profile together)."""
    context = await build_candidate_context(
        github_url=github_url,
        linkedin_text=linkedin_text,
        linkedin_pdf=await read_pdf(linkedin_pdf),
        resume_pdf=await read_pdf(resume_pdf),
    )

    config = InterviewConfig(
        role_title=role_title,
        seniority=seniority,
        interviewer_level=interviewer_level,
        duration_minutes=max(1, min(60, duration_minutes)),
        focus_areas=[a.strip() for a in focus_areas.split(",") if a.strip()],
    )
    session = InterviewSession(config=config, context=context)
    get_repository().create(session)

    return {
        "id": session.id,
        "state": session.state.value,
        "config": config.model_dump(mode="json"),
        "context": context.model_dump(mode="json"),
    }


@router.get("/sessions", dependencies=[Depends(require_admin)])
def list_sessions(
    invite_id: str | None = None,
    state: str | None = None,
    decision: str | None = None,  # "forward" | "no" | "pending"
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """Admin: filtered, paginated session summaries (newest first)."""
    limit = max(1, min(100, limit))
    offset = max(0, offset)
    items, total = get_repository().query_session_summaries(
        invite_id=invite_id, state=state, decision=decision, q=q, limit=limit, offset=offset
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.delete("/sessions/{session_id}", dependencies=[Depends(require_admin)])
def delete_session(session_id: str):
    if not get_repository().delete_session(session_id):
        raise HTTPException(404, "session not found")
    return {"status": "deleted", "id": session_id}


@router.get("/sessions/{session_id}", dependencies=[Depends(require_admin)])
def get_session(session_id: str):
    session = get_repository().get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    return session.model_dump(mode="json")


@router.post("/sessions/{session_id}/finish")
async def finish_session(session_id: str):
    """Force wrap-up + evaluation (used by the client's idle/deadline timer)."""
    repo = get_repository()
    session = repo.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")

    if session.evaluation is None:
        session.finish_requested = True
        session.state = InterviewState.EVALUATION
        try:
            session.evaluation = await get_evaluator().evaluate(session)
        except Exception as exc:
            session.state = InterviewState.WRAP_UP
            repo.save(session)
            raise HTTPException(
                503,
                "Could not evaluate: the AI model errored (likely quota/rate limit). "
                "Please retry shortly.",
            ) from exc
        session.state = InterviewState.COMPLETE
        repo.save(session)

    return session.evaluation.model_dump(mode="json")


@router.post("/sessions/{session_id}/feedback")
def submit_feedback(session_id: str, feedback: Feedback):
    """Capture post-interview feedback to help mature the product."""
    repo = get_repository()
    session = repo.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    session.feedback = feedback
    repo.save(session)
    return {"status": "ok", "feedback": feedback.model_dump(mode="json")}


@router.get("/sessions/{session_id}/result", dependencies=[Depends(require_admin)])
def get_result(session_id: str):
    session = get_repository().get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    if session.evaluation is None:
        raise HTTPException(409, "evaluation not ready yet")
    return {
        "id": session.id,
        "config": session.config.model_dump(mode="json"),
        "context": session.context.model_dump(mode="json"),
        "evaluation": session.evaluation.model_dump(mode="json"),
        "transcript": [t.model_dump(mode="json") for t in session.transcript],
        "feedback": session.feedback.model_dump(mode="json") if session.feedback else None,
    }
