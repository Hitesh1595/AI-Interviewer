"""State machine pattern: deterministic, time-driven interview flow.

Flow (a real interview shape):
    GREETING      interviewer introduces itself + asks candidate to introduce
    QUESTIONING   main profile-grounded questions + follow-ups
    WRAP_UP       invite candidate questions, closing remarks
    EVALUATION    (transient) run the rubric evaluation
    COMPLETE      done

`decide` is a pure function of the session's observable state and is called by
the engine after each candidate reply, so it is trivially unit-testable.
"""
from __future__ import annotations

from app.domain.enums import InterviewState

# Fraction of the time budget after which we begin wrapping up.
WRAP_UP_FRACTION = 0.85


class InterviewStateMachine:
    def __init__(self, question_budget: int) -> None:
        self.question_budget = question_budget

    def decide(
        self,
        *,
        state: InterviewState,
        elapsed_fraction: float,
        interviewer_turns: int,
        finish_requested: bool,
    ) -> InterviewState:
        # Terminal states never move.
        if state in (InterviewState.EVALUATION, InterviewState.COMPLETE):
            return state

        # An explicit finish request short-circuits toward evaluation.
        if finish_requested:
            return (
                InterviewState.EVALUATION
                if state == InterviewState.WRAP_UP
                else InterviewState.WRAP_UP
            )

        if state == InterviewState.GREETING:
            # Candidate has just answered the introduction -> begin questioning.
            return InterviewState.QUESTIONING

        if state in (InterviewState.QUESTIONING, InterviewState.FOLLOW_UP):
            out_of_time = elapsed_fraction >= WRAP_UP_FRACTION
            out_of_questions = interviewer_turns >= self.question_budget
            return (
                InterviewState.WRAP_UP
                if (out_of_time or out_of_questions)
                else InterviewState.QUESTIONING
            )

        if state == InterviewState.WRAP_UP:
            # Candidate has responded during wrap-up -> evaluate.
            return InterviewState.EVALUATION

        return state

    @staticmethod
    def phase_directive(state: InterviewState) -> str:
        """Human-readable instruction injected into the prompt for this phase."""
        return {
            InterviewState.GREETING: (
                "Introduce yourself as the interviewer for this role in one or two "
                "sentences, briefly explain how the interview will go, then warmly "
                "ask the candidate to introduce themselves. Ask exactly one thing."
            ),
            InterviewState.QUESTIONING: (
                "Ask your next interview question. Ground it in the candidate's real "
                "projects and tech stack when possible. Acknowledge their previous "
                "answer in one short sentence first, then ask ONE focused question."
            ),
            InterviewState.FOLLOW_UP: (
                "Ask a pointed follow-up that digs deeper into the candidate's "
                "previous answer. Keep it to ONE question."
            ),
            InterviewState.WRAP_UP: (
                "Begin wrapping up. Briefly thank the candidate, invite them to ask "
                "you one or two questions about the role, and signal the interview "
                "is nearly over. Keep it short."
            ),
        }.get(state, "Continue the interview naturally with one question.")
