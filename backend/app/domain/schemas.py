"""Pydantic domain models shared across services."""
from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import (
    InterviewerLevel,
    InterviewState,
    Recommendation,
    Seniority,
)


class InterviewConfig(BaseModel):
    role_title: str  # the position being interviewed for (required)
    candidate_name: str | None = None  # admin-provided name (shown in dashboard)
    seniority: Seniority
    interviewer_level: InterviewerLevel = InterviewerLevel.BALANCED
    duration_minutes: int = 15
    focus_areas: list[str] = Field(default_factory=list)


class InterviewInvite(BaseModel):
    """Admin-created interview template. Shared with a candidate as a link."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_ts: float = Field(default_factory=time.time)
    config: "InterviewConfig"


class ProjectSignal(BaseModel):
    name: str
    description: str = ""
    tech: list[str] = Field(default_factory=list)
    url: str = ""
    source: str = ""


class ProfileFragment(BaseModel):
    """Normalized output of a single profile adapter."""

    source: str
    summary: str = ""
    signals: dict = Field(default_factory=dict)
    raw_excerpt: str = ""


class CandidateContext(BaseModel):
    """Aggregated, deduplicated view of everything we know about the candidate."""

    candidate_name: str | None = None
    fragments: list[ProfileFragment] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    projects: list[ProjectSignal] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    available_sources: list[str] = Field(default_factory=list)


class Turn(BaseModel):
    role: Literal["interviewer", "candidate"]
    content: str
    ts: float = Field(default_factory=time.time)


class Feedback(BaseModel):
    """Post-interview feedback from the candidate/recruiter to improve the product."""

    rating: int = Field(ge=1, le=5)  # 1-5 stars on the interview experience
    comment: str = ""
    would_recommend: bool | None = None
    ts: float = Field(default_factory=time.time)


class Evaluation(BaseModel):
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0  # out of 10
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    summary: str = ""
    recommendation: Recommendation = Recommendation.NO
    move_forward: bool = False


class InterviewSession(BaseModel):
    """The full aggregate the engine and repository operate on."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    invite_id: str | None = None
    created_ts: float = Field(default_factory=time.time)
    started_ts: float | None = None
    deadline_ts: float | None = None
    state: InterviewState = InterviewState.GREETING
    finish_requested: bool = False
    config: InterviewConfig
    context: CandidateContext
    transcript: list[Turn] = Field(default_factory=list)
    evaluation: Evaluation | None = None
    feedback: Feedback | None = None

    @property
    def interviewer_turns(self) -> int:
        return sum(1 for t in self.transcript if t.role == "interviewer")

    def elapsed_fraction(self, now: float | None = None) -> float:
        if not self.started_ts or not self.deadline_ts:
            return 0.0
        now = now if now is not None else time.time()
        span = self.deadline_ts - self.started_ts
        if span <= 0:
            return 1.0
        return max(0.0, min(1.0, (now - self.started_ts) / span))
