"""Repository pattern: hides SQLite behind domain-object CRUD.

The rest of the app deals only in `InterviewSession` domain objects; this class
maps them to/from the `SessionRecord` table. It opens a short-lived DB session
per operation so it is safe to use from the long-lived WebSocket handler.
"""
from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.domain.enums import InterviewState
from app.domain.schemas import (
    CandidateContext,
    Evaluation,
    Feedback,
    InterviewConfig,
    InterviewInvite,
    InterviewSession,
)
from app.models.db_models import InviteRecord, SessionRecord


class SessionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # --- mapping helpers -------------------------------------------------
    @staticmethod
    def _to_record(s: InterviewSession) -> SessionRecord:
        return SessionRecord(
            id=s.id,
            invite_id=s.invite_id,
            created_ts=s.created_ts,
            started_ts=s.started_ts,
            deadline_ts=s.deadline_ts,
            state=s.state.value,
            finish_requested=s.finish_requested,
            config=s.config.model_dump(mode="json"),
            context=s.context.model_dump(mode="json"),
            transcript=[t.model_dump(mode="json") for t in s.transcript],
            evaluation=s.evaluation.model_dump(mode="json") if s.evaluation else None,
            feedback=s.feedback.model_dump(mode="json") if s.feedback else None,
        )

    @staticmethod
    def _to_domain(r: SessionRecord) -> InterviewSession:
        return InterviewSession(
            id=r.id,
            invite_id=r.invite_id,
            created_ts=r.created_ts,
            started_ts=r.started_ts,
            deadline_ts=r.deadline_ts,
            state=InterviewState(r.state),
            finish_requested=r.finish_requested,
            config=InterviewConfig.model_validate(r.config),
            context=CandidateContext.model_validate(r.context),
            transcript=r.transcript or [],
            evaluation=Evaluation.model_validate(r.evaluation)
            if r.evaluation
            else None,
            feedback=Feedback.model_validate(r.feedback) if r.feedback else None,
        )

    # --- invites ---------------------------------------------------------
    def create_invite(self, invite: InterviewInvite) -> InterviewInvite:
        with Session(self._engine) as db:
            db.add(
                InviteRecord(
                    id=invite.id,
                    created_ts=invite.created_ts,
                    config=invite.config.model_dump(mode="json"),
                )
            )
            db.commit()
        return invite

    def get_invite(self, invite_id: str) -> InterviewInvite | None:
        with Session(self._engine) as db:
            record = db.get(InviteRecord, invite_id)
            if not record:
                return None
            return InterviewInvite(
                id=record.id,
                created_ts=record.created_ts,
                config=InterviewConfig.model_validate(record.config),
            )

    def list_invites(self) -> list[InterviewInvite]:
        with Session(self._engine) as db:
            records = db.exec(select(InviteRecord)).all()
            return [
                InterviewInvite(
                    id=r.id,
                    created_ts=r.created_ts,
                    config=InterviewConfig.model_validate(r.config),
                )
                for r in records
            ]

    def list_session_summaries(self, invite_id: str | None = None) -> list[dict]:
        """Lightweight session rows for the admin dashboard (no transcript)."""
        with Session(self._engine) as db:
            stmt = select(SessionRecord)
            if invite_id:
                stmt = stmt.where(SessionRecord.invite_id == invite_id)
            rows = db.exec(stmt).all()

        summaries = []
        for r in rows:
            ev = r.evaluation or None
            fb = r.feedback or None
            summaries.append(
                {
                    "id": r.id,
                    "invite_id": r.invite_id,
                    "created_ts": r.created_ts,
                    "state": r.state,
                    "candidate_name": (r.config or {}).get("candidate_name")
                    or (r.context or {}).get("candidate_name"),
                    "role_title": (r.config or {}).get("role_title"),
                    "seniority": (r.config or {}).get("seniority"),
                    "overall_score": ev.get("overall_score") if ev else None,
                    "move_forward": ev.get("move_forward") if ev else None,
                    "recommendation": ev.get("recommendation") if ev else None,
                    "feedback_rating": fb.get("rating") if fb else None,
                }
            )
        summaries.sort(key=lambda s: s["created_ts"], reverse=True)
        return summaries

    def query_session_summaries(
        self,
        *,
        invite_id: str | None = None,
        state: str | None = None,
        decision: str | None = None,  # "forward" | "no" | "pending"
        q: str | None = None,  # candidate name search
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        rows = self.list_session_summaries(invite_id)

        def keep(s: dict) -> bool:
            if state and s["state"] != state:
                return False
            if decision == "pending" and s["move_forward"] is not None:
                return False
            if decision == "forward" and s["move_forward"] is not True:
                return False
            if decision == "no" and s["move_forward"] is not False:
                return False
            if q and q.lower() not in (s["candidate_name"] or "").lower():
                return False
            return True

        filtered = [s for s in rows if keep(s)]
        total = len(filtered)
        return filtered[offset : offset + limit], total

    def delete_session(self, session_id: str) -> bool:
        with Session(self._engine) as db:
            rec = db.get(SessionRecord, session_id)
            if not rec:
                return False
            db.delete(rec)
            db.commit()
            return True

    def delete_invite(self, invite_id: str) -> bool:
        """Delete an invite and all sessions started from it."""
        with Session(self._engine) as db:
            invite = db.get(InviteRecord, invite_id)
            sessions = db.exec(
                select(SessionRecord).where(SessionRecord.invite_id == invite_id)
            ).all()
            for s in sessions:
                db.delete(s)
            if invite:
                db.delete(invite)
            db.commit()
            return invite is not None

    # --- sessions --------------------------------------------------------
    def create(self, session: InterviewSession) -> InterviewSession:
        with Session(self._engine) as db:
            db.add(self._to_record(session))
            db.commit()
        return session

    def get(self, session_id: str) -> InterviewSession | None:
        with Session(self._engine) as db:
            record = db.get(SessionRecord, session_id)
            return self._to_domain(record) if record else None

    def save(self, session: InterviewSession) -> InterviewSession:
        """Upsert the full session state."""
        with Session(self._engine) as db:
            record = db.get(SessionRecord, session.id)
            new = self._to_record(session)
            if record is None:
                db.add(new)
            else:
                for field, value in new.model_dump().items():
                    setattr(record, field, value)
                db.add(record)
            db.commit()
        return session
