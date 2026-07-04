import pytest

from app.domain.enums import InterviewerLevel, Seniority
from app.domain.strategies import RUBRIC_DIMENSIONS, get_strategy


@pytest.mark.parametrize("seniority", list(Seniority))
@pytest.mark.parametrize("level", list(InterviewerLevel))
def test_weights_sum_to_one_and_cover_dimensions(seniority, level):
    strat = get_strategy(seniority, level)
    assert set(strat.rubric_weights) == set(RUBRIC_DIMENSIONS)
    assert abs(sum(strat.rubric_weights.values()) - 1.0) < 1e-6


def test_rigorous_threshold_higher_than_supportive():
    senior_soft = get_strategy(Seniority.SENIOR, InterviewerLevel.SUPPORTIVE)
    senior_hard = get_strategy(Seniority.SENIOR, InterviewerLevel.RIGOROUS)
    assert senior_hard.pass_threshold > senior_soft.pass_threshold


def test_senior_has_larger_question_budget_than_intern():
    intern = get_strategy(Seniority.INTERN, InterviewerLevel.BALANCED)
    senior = get_strategy(Seniority.SENIOR, InterviewerLevel.BALANCED)
    assert senior.question_budget >= intern.question_budget


def test_threshold_clamped_within_bounds():
    for seniority in Seniority:
        for level in InterviewerLevel:
            strat = get_strategy(seniority, level)
            assert 0.0 <= strat.pass_threshold <= 10.0
