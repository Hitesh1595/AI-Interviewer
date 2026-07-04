"""Core enumerations for the interview domain."""
from enum import Enum


class Seniority(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    SENIOR = "senior"


class InterviewerLevel(str, Enum):
    SUPPORTIVE = "supportive"
    BALANCED = "balanced"
    RIGOROUS = "rigorous"


class InterviewState(str, Enum):
    GREETING = "greeting"
    QUESTIONING = "questioning"
    FOLLOW_UP = "follow_up"
    WRAP_UP = "wrap_up"
    EVALUATION = "evaluation"
    COMPLETE = "complete"


class Recommendation(str, Enum):
    STRONG_NO = "strong_no"
    NO = "no"
    YES = "yes"
    STRONG_YES = "strong_yes"

    @property
    def moves_forward(self) -> bool:
        return self in (Recommendation.YES, Recommendation.STRONG_YES)
