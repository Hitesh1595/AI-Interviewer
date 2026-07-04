"""SQLModel table definitions. Complex fields are stored as JSON columns."""
from __future__ import annotations

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class InviteRecord(SQLModel, table=True):
    __tablename__ = "invites"

    id: str = Field(primary_key=True)
    created_ts: float
    config: dict = Field(default_factory=dict, sa_column=Column(JSON))


class SessionRecord(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(primary_key=True)
    invite_id: str | None = Field(default=None, index=True)
    created_ts: float
    started_ts: float | None = None
    deadline_ts: float | None = None
    state: str = "greeting"
    finish_requested: bool = False

    config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    context: dict = Field(default_factory=dict, sa_column=Column(JSON))
    transcript: list = Field(default_factory=list, sa_column=Column(JSON))
    evaluation: dict | None = Field(default=None, sa_column=Column(JSON))
    feedback: dict | None = Field(default=None, sa_column=Column(JSON))
