import pytest

from app.domain.enums import InterviewerLevel, Recommendation, Seniority
from app.domain.schemas import (
    CandidateContext,
    InterviewConfig,
    InterviewSession,
    Turn,
)
from app.services.evaluation.evaluator import EvaluationService, parse_json_lenient


def test_parse_json_plain():
    assert parse_json_lenient('{"a": 1}') == {"a": 1}


def test_parse_json_with_code_fence():
    raw = '```json\n{"a": 1, "b": [2, 3]}\n```'
    assert parse_json_lenient(raw) == {"a": 1, "b": [2, 3]}


def test_parse_json_with_surrounding_prose():
    raw = 'Sure! Here is the result:\n{"score": 8}\nHope that helps.'
    assert parse_json_lenient(raw) == {"score": 8}


def test_parse_json_garbage_returns_empty():
    assert parse_json_lenient("not json at all") == {}


class _StubLLM:
    def __init__(self, payload: str):
        self._payload = payload

    async def generate_json(self, *, system_instruction: str, prompt: str, temperature: float = 0.2):
        return self._payload

    def stream(self, **kwargs):  # not used here
        raise NotImplementedError


def _session():
    return InterviewSession(
        config=InterviewConfig(
            role_title="Backend Engineer",
            seniority=Seniority.JUNIOR,
            interviewer_level=InterviewerLevel.BALANCED,
        ),
        context=CandidateContext(),
        transcript=[
            Turn(role="interviewer", content="Tell me about yourself."),
            Turn(role="candidate", content="I build APIs with FastAPI."),
        ],
    )


@pytest.mark.asyncio
async def test_evaluate_computes_weighted_overall_and_move_forward():
    payload = (
        '{"dimension_scores": {"technical_depth": 8, "problem_solving": 8, '
        '"communication": 8, "experience_relevance": 8, "behavioral": 8}, '
        '"strengths": ["clear"], "weaknesses": ["shallow"], '
        '"summary": "solid", "recommendation": "yes"}'
    )
    evaluation = await EvaluationService(_StubLLM(payload)).evaluate(_session())
    assert evaluation.overall_score == pytest.approx(8.0, abs=0.01)
    assert evaluation.move_forward is True
    assert evaluation.recommendation == Recommendation.YES


@pytest.mark.asyncio
async def test_evaluate_low_scores_do_not_move_forward():
    payload = (
        '{"dimension_scores": {"technical_depth": 3, "problem_solving": 3, '
        '"communication": 3, "experience_relevance": 3, "behavioral": 3}, '
        '"recommendation": "no"}'
    )
    evaluation = await EvaluationService(_StubLLM(payload)).evaluate(_session())
    assert evaluation.overall_score == pytest.approx(3.0, abs=0.01)
    assert evaluation.move_forward is False
