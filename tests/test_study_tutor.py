"""Study-tutor prompt-builder tests (issue #7, ADR-0004).

The study tutor receives no due items and emits no eval blocks. Its prompt
carries the subject, subject memory, recent session summaries, and a phase hint
(level check / work / reflection / wind-down). These assert the pure builder's
output at the API boundary — no LLM call.
"""

import pytest

from studyhelp.tutor import (
    STUDY_PHASES,
    STUDY_SYSTEM_PROMPT,
    build_study_messages,
)


def test_study_prompt_has_no_due_items_or_eval_contract():
    # ADR-0004: study chat teaches; it must not quiz a due deck or write reviews.
    assert "<eval>" not in STUDY_SYSTEM_PROMPT
    assert "item_ref" not in STUDY_SYSTEM_PROMPT
    assert "due" not in STUDY_SYSTEM_PROMPT.lower()


def test_opener_carries_subject_memory_and_phase_when_no_messages():
    api_messages = build_study_messages(
        phase="level_check",
        subject_name="Linear Algebra",
        messages=[],
        subject_memory="Comfortable with matrices; shaky on eigenvalues.",
        recent_summaries=["Covered matrix multiplication and the identity."],
    )
    assert len(api_messages) == 1
    assert api_messages[0]["role"] == "user"
    context = api_messages[0]["content"]
    assert "Linear Algebra" in context
    assert "level check" in context.lower()
    assert "eigenvalues" in context  # memory surfaced
    assert "matrix multiplication" in context  # recent summary surfaced


def test_context_prepended_only_to_first_user_message():
    prior = [
        {"role": "assistant", "content": "What's a basis?"},
        {"role": "user", "content": "A minimal spanning set."},
    ]
    api_messages = build_study_messages(
        phase="reflection",
        subject_name="Linear Algebra",
        messages=prior,
        subject_memory=None,
        recent_summaries=None,
    )
    # Same number of turns; context is folded into the first user turn only.
    assert len(api_messages) == 2
    assert api_messages[0]["role"] == "assistant"
    assert api_messages[0]["content"] == "What's a basis?"
    assert "reflection" in api_messages[1]["content"].lower()
    assert "A minimal spanning set." in api_messages[1]["content"]


def test_unknown_phase_is_rejected():
    with pytest.raises(ValueError):
        build_study_messages(phase="quiz", subject_name="X", messages=[])


def test_known_phases_are_the_four_pomodoro_phases():
    assert set(STUDY_PHASES) == {"level_check", "work", "reflection", "wind_down"}
