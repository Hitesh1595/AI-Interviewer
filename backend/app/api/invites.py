"""Admin creates an invite (master settings); candidate starts from the link."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.auth import require_admin
from app.api.deps import get_repository
from app.domain.schemas import (
    InterviewConfig,
    InterviewInvite,
    InterviewSession,
)
from app.services.intake import build_candidate_context, read_pdf

router = APIRouter(prefix="/api/invites", tags=["invites"])


@router.post("", dependencies=[Depends(require_admin)])
def create_invite(config: InterviewConfig):
    """Admin endpoint: store the master settings, return a shareable invite."""
    invite = InterviewInvite(config=config)
    get_repository().create_invite(invite)
    return {
        "id": invite.id,
        "link_path": f"/invite/{invite.id}",
        "config": invite.config.model_dump(mode="json"),
    }


@router.get("", dependencies=[Depends(require_admin)])
def list_invites():
    """Admin: all invites with how many candidates have started each."""
    repo = get_repository()
    invites = repo.list_invites()
    summaries = repo.list_session_summaries()
    counts: dict[str, int] = {}
    for s in summaries:
        counts[s["invite_id"]] = counts.get(s["invite_id"], 0) + 1
    result = [
        {
            "id": i.id,
            "created_ts": i.created_ts,
            "config": i.config.model_dump(mode="json"),
            "link_path": f"/invite/{i.id}",
            "session_count": counts.get(i.id, 0),
        }
        for i in invites
    ]
    result.sort(key=lambda x: x["created_ts"], reverse=True)
    return result


@router.get("/{invite_id}")
def get_invite(invite_id: str):
    """Public: what the candidate sees before starting (role, seniority, etc.)."""
    invite = get_repository().get_invite(invite_id)
    if not invite:
        raise HTTPException(404, "invite not found")
    return {"id": invite.id, "config": invite.config.model_dump(mode="json")}


@router.delete("/{invite_id}", dependencies=[Depends(require_admin)])
def delete_invite(invite_id: str):
    """Admin: delete an invite and all sessions started from it."""
    if not get_repository().delete_invite(invite_id):
        raise HTTPException(404, "invite not found")
    return {"status": "deleted", "id": invite_id}


@router.post("/{invite_id}/start")
async def start_from_invite(
    invite_id: str,
    github_url: str = Form(""),
    linkedin_text: str = Form(""),
    linkedin_pdf: UploadFile | None = File(None),
    resume_pdf: UploadFile | None = File(None),
):
    """Candidate endpoint: submit profile, create a session from the invite config."""
    repo = get_repository()
    invite = repo.get_invite(invite_id)
    if not invite:
        raise HTTPException(404, "invite not found")

    context = await build_candidate_context(
        github_url=github_url,
        linkedin_text=linkedin_text,
        linkedin_pdf=await read_pdf(linkedin_pdf),
        resume_pdf=await read_pdf(resume_pdf),
    )
    # Admin-provided name takes priority for greeting + dashboard display.
    if invite.config.candidate_name:
        context.candidate_name = invite.config.candidate_name
    session = InterviewSession(
        invite_id=invite.id, config=invite.config, context=context
    )
    repo.create(session)
    return {
        "id": session.id,
        "state": session.state.value,
        "context": context.model_dump(mode="json"),
    }
