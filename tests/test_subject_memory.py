"""Tests for the study-service subject-memory and summary additions (issue #5).

Layered on the phased study session (#7): the session summary is stored on the
session, and the subject memory is rewritten wholesale (never appended) after
each session and capped in length. Driven at the service seam with LLM output
fed past the boundary as plain strings.
"""

from datetime import timedelta

from studyhelp.study import (
    MEMORY_CHAR_CAP,
    get_subject_memory,
    recent_summaries,
    rewrite_subject_memory,
    start_study_session,
    store_summary,
)
from tests.conftest import BASE_DAY


def test_subject_memory_is_empty_before_any_write(db, seed):
    subj = seed.subject()
    assert get_subject_memory(db, seed.user.id, subj.id) == ""


def test_subject_memory_is_rewritten_not_appended(db, seed):
    subj = seed.subject()
    rewrite_subject_memory(db, seed.user.id, subj.id, "First memory.")
    assert get_subject_memory(db, seed.user.id, subj.id) == "First memory."

    rewrite_subject_memory(db, seed.user.id, subj.id, "Second replaces first.")
    mem = get_subject_memory(db, seed.user.id, subj.id)
    assert mem == "Second replaces first."
    assert "First memory." not in mem


def test_subject_memory_is_length_capped(db, seed):
    subj = seed.subject()
    rewrite_subject_memory(db, seed.user.id, subj.id, "x" * (MEMORY_CHAR_CAP + 5000))
    assert len(get_subject_memory(db, seed.user.id, subj.id)) <= MEMORY_CHAR_CAP


def test_store_summary_and_recent_summaries_newest_first(db, seed):
    subj = seed.subject()
    for i in range(3):
        s = start_study_session(db, seed.user.id, subj.id)
        # sessions are ordered by started_at; nudge them apart deterministically
        s.started_at = BASE_DAY + timedelta(days=i)
        store_summary(db, s.id, f"summary {i}")

    summaries = recent_summaries(db, seed.user.id, subj.id, limit=2)
    assert [s.summary for s in summaries] == ["summary 2", "summary 1"]


def test_sessions_without_a_summary_are_not_listed(db, seed):
    subj = seed.subject()
    start_study_session(db, seed.user.id, subj.id)  # no summary stored
    assert recent_summaries(db, seed.user.id, subj.id) == []
