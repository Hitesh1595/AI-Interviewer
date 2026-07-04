from app.domain.enums import InterviewState
from app.domain.state_machine import InterviewStateMachine


def sm(budget=5):
    return InterviewStateMachine(question_budget=budget)


def test_greeting_advances_to_questioning():
    assert sm().decide(
        state=InterviewState.GREETING,
        elapsed_fraction=0.1,
        interviewer_turns=1,
        finish_requested=False,
    ) == InterviewState.QUESTIONING


def test_questioning_stays_until_budget_or_time():
    assert sm(budget=5).decide(
        state=InterviewState.QUESTIONING,
        elapsed_fraction=0.3,
        interviewer_turns=2,
        finish_requested=False,
    ) == InterviewState.QUESTIONING


def test_questioning_wraps_when_out_of_questions():
    assert sm(budget=3).decide(
        state=InterviewState.QUESTIONING,
        elapsed_fraction=0.3,
        interviewer_turns=3,
        finish_requested=False,
    ) == InterviewState.WRAP_UP


def test_questioning_wraps_when_out_of_time():
    assert sm(budget=10).decide(
        state=InterviewState.QUESTIONING,
        elapsed_fraction=0.9,
        interviewer_turns=2,
        finish_requested=False,
    ) == InterviewState.WRAP_UP


def test_wrap_up_moves_to_evaluation():
    assert sm().decide(
        state=InterviewState.WRAP_UP,
        elapsed_fraction=0.95,
        interviewer_turns=6,
        finish_requested=False,
    ) == InterviewState.EVALUATION


def test_finish_request_forces_wrap_then_eval():
    assert sm().decide(
        state=InterviewState.QUESTIONING,
        elapsed_fraction=0.2,
        interviewer_turns=1,
        finish_requested=True,
    ) == InterviewState.WRAP_UP
    assert sm().decide(
        state=InterviewState.WRAP_UP,
        elapsed_fraction=0.2,
        interviewer_turns=1,
        finish_requested=True,
    ) == InterviewState.EVALUATION


def test_terminal_states_do_not_move():
    for terminal in (InterviewState.EVALUATION, InterviewState.COMPLETE):
        assert sm().decide(
            state=terminal,
            elapsed_fraction=1.0,
            interviewer_turns=9,
            finish_requested=True,
        ) == terminal
