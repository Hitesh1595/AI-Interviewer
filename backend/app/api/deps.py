"""Dependency-injection providers wiring services together."""
from __future__ import annotations

from functools import lru_cache

from app.db import engine
from app.repository.session_repo import SessionRepository
from app.services.evaluation.evaluator import EvaluationService
from app.services.interview.engine import InterviewEngine
from app.services.interview.prompt_builder import PromptBuilder
from app.services.llm.factory import get_llm_provider


@lru_cache
def get_repository() -> SessionRepository:
    return SessionRepository(engine)


@lru_cache
def get_engine() -> InterviewEngine:
    return InterviewEngine(get_llm_provider(), PromptBuilder())


@lru_cache
def get_evaluator() -> EvaluationService:
    return EvaluationService(get_llm_provider())
