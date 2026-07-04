"""Strategy pattern: seniority + interviewer level determine interview behavior.

Combining a `Seniority` base profile with an `InterviewerLevel` modifier yields
an `InterviewStrategy` that drives question difficulty, count, tone, rubric
weights, and the pass threshold used for the move-forward decision.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.enums import InterviewerLevel, Seniority

# Rubric dimensions scored 0-10 each; weights per dimension sum to 1.0.
RUBRIC_DIMENSIONS = [
    "technical_depth",
    "problem_solving",
    "communication",
    "experience_relevance",
    "behavioral",
]


class InterviewStrategy(BaseModel):
    seniority: Seniority
    interviewer_level: InterviewerLevel
    question_budget: int  # target number of main interviewer questions
    difficulty: str
    tone: str
    follow_up_intensity: str
    rubric_weights: dict[str, float]
    pass_threshold: float  # overall /10 needed to move forward
    guidance: str = Field(default="")


# Base profile per seniority: difficulty, question budget, rubric weights, threshold.
_SENIORITY_BASE: dict[Seniority, dict] = {
    Seniority.INTERN: {
        "question_budget": 4,
        "difficulty": "foundational fundamentals and coursework/side-project level",
        "pass_threshold": 6.0,
        "weights": {
            "technical_depth": 0.20,
            "problem_solving": 0.25,
            "communication": 0.25,
            "experience_relevance": 0.10,
            "behavioral": 0.20,
        },
        "guidance": (
            "Focus on fundamentals, learning ability, and enthusiasm. It is fine "
            "if the candidate lacks production experience; probe how they reason."
        ),
    },
    Seniority.JUNIOR: {
        "question_budget": 5,
        "difficulty": "practical, day-to-day engineering at 0-2 years experience",
        "pass_threshold": 6.5,
        "weights": {
            "technical_depth": 0.30,
            "problem_solving": 0.25,
            "communication": 0.20,
            "experience_relevance": 0.15,
            "behavioral": 0.10,
        },
        "guidance": (
            "Probe hands-on experience from their real projects, debugging habits, "
            "and understanding of the tools they claim to know."
        ),
    },
    Seniority.SENIOR: {
        "question_budget": 6,
        "difficulty": "advanced: system design, trade-offs, leadership, and depth",
        "pass_threshold": 7.0,
        "weights": {
            "technical_depth": 0.30,
            "problem_solving": 0.25,
            "communication": 0.15,
            "experience_relevance": 0.20,
            "behavioral": 0.10,
        },
        "guidance": (
            "Push on architecture decisions, trade-offs, scale, mentoring, and "
            "ownership. Challenge answers and expect justification."
        ),
    },
}

# Modifier per interviewer level: tone, follow-up intensity, threshold delta.
_LEVEL_MODIFIER: dict[InterviewerLevel, dict] = {
    InterviewerLevel.SUPPORTIVE: {
        "tone": "warm, encouraging, and patient; offer small hints if the candidate is stuck",
        "follow_up_intensity": "light",
        "threshold_delta": -0.5,
    },
    InterviewerLevel.BALANCED: {
        "tone": "professional, neutral, and fair",
        "follow_up_intensity": "moderate",
        "threshold_delta": 0.0,
    },
    InterviewerLevel.RIGOROUS: {
        "tone": "probing and demanding; politely challenge weak answers and dig deeper",
        "follow_up_intensity": "heavy",
        "threshold_delta": 0.5,
    },
}


def get_strategy(
    seniority: Seniority, interviewer_level: InterviewerLevel
) -> InterviewStrategy:
    base = _SENIORITY_BASE[seniority]
    mod = _LEVEL_MODIFIER[interviewer_level]
    threshold = max(0.0, min(10.0, base["pass_threshold"] + mod["threshold_delta"]))
    return InterviewStrategy(
        seniority=seniority,
        interviewer_level=interviewer_level,
        question_budget=base["question_budget"],
        difficulty=base["difficulty"],
        tone=mod["tone"],
        follow_up_intensity=mod["follow_up_intensity"],
        rubric_weights=base["weights"],
        pass_threshold=threshold,
        guidance=base["guidance"],
    )
