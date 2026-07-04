"""Evaluation service: turn a transcript into a structured, weighted score.

Sends the transcript + rubric to the LLM in JSON mode, parses defensively (with
a bracket-extraction repair fallback), computes the weighted overall /10 from the
strategy weights, and derives the move-forward decision from the pass threshold.
"""
from __future__ import annotations

import json

from app.domain.enums import Recommendation
from app.domain.schemas import Evaluation, InterviewSession
from app.domain.strategies import RUBRIC_DIMENSIONS, InterviewStrategy, get_strategy
from app.services.llm.base import LLMProvider

_SYSTEM = (
    "You are a fair, rigorous hiring evaluator. You output ONLY valid JSON that "
    "matches the requested schema. Base every judgement strictly on the interview "
    "transcript provided; never invent facts."
)


def _clamp(x: float) -> float:
    return max(0.0, min(10.0, float(x)))


def parse_json_lenient(raw: str) -> dict:
    """Parse JSON, repairing common LLM issues (code fences, surrounding prose)."""
    if not raw:
        return {}
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


class EvaluationService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def _build_prompt(
        self, session: InterviewSession, strategy: InterviewStrategy
    ) -> str:
        transcript = "\n".join(
            f"{'INTERVIEWER' if t.role == 'interviewer' else 'CANDIDATE'}: {t.content}"
            for t in session.transcript
        )
        weights = ", ".join(f"{k}={v}" for k, v in strategy.rubric_weights.items())
        return f"""Evaluate this interview for the role "{session.config.role_title}" \
at the {session.config.seniority.value.upper()} level.

Score each rubric dimension from 0 to 10 (integers or one decimal). Dimensions:
{', '.join(RUBRIC_DIMENSIONS)}
(Rubric weights for context: {weights}. Pass threshold: {strategy.pass_threshold}/10.)

Return JSON with EXACTLY this shape:
{{
  "dimension_scores": {{ {', '.join(f'"{d}": <0-10>' for d in RUBRIC_DIMENSIONS)} }},
  "strengths": ["..."],
  "weaknesses": ["..."],
  "summary": "2-4 sentence overall summary of the conversation and the candidate",
  "recommendation": "strong_no | no | yes | strong_yes"
}}

INTERVIEW TRANSCRIPT:
{transcript}
"""

    async def evaluate(self, session: InterviewSession) -> Evaluation:
        strategy = get_strategy(
            session.config.seniority, session.config.interviewer_level
        )
        raw = await self._llm.generate_json(
            system_instruction=_SYSTEM,
            prompt=self._build_prompt(session, strategy),
        )
        data = parse_json_lenient(raw)

        scores_in = data.get("dimension_scores", {}) or {}
        dimension_scores = {
            d: _clamp(scores_in.get(d, 0)) for d in RUBRIC_DIMENSIONS
        }

        overall = round(
            sum(dimension_scores[d] * strategy.rubric_weights[d] for d in RUBRIC_DIMENSIONS),
            2,
        )

        try:
            recommendation = Recommendation(data.get("recommendation", "no"))
        except ValueError:
            recommendation = Recommendation.NO

        # Move-forward is driven by the weighted score vs threshold; the LLM's
        # categorical recommendation is kept as the qualitative call.
        move_forward = overall >= strategy.pass_threshold

        return Evaluation(
            dimension_scores=dimension_scores,
            overall_score=overall,
            strengths=list(data.get("strengths", []) or []),
            weaknesses=list(data.get("weaknesses", []) or []),
            summary=data.get("summary", "") or "",
            recommendation=recommendation,
            move_forward=move_forward,
        )
