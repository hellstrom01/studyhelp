"""Study-session service tests (issue #7).

Interval accounting and transcript/notes persistence for the phased study
session (ADR-0004): the server accumulates work-interval seconds from explicit
interval start/end calls; level-check and break time are never counted; chat
messages and notes persist server-side. Study sessions produce no Review rows.
"""

from datetime import timedelta

import pytest

from tests.conftest import BASE_DAY
from studyhelp.models import StudySession
from studyhelp.study import (
    append_message,
    end_interval,
    end_study_session,
    get_transcript,
    save_notes,
    start_interval,
    start_study_session,
)


def test_work_seconds_accumulate_only_across_intervals(db, seed):
    subj = seed.subject("Linear Algebra")
    session = start_study_session(db, seed.user.id, subj.id)

    # Level check runs untimed for 10 minutes before the first interval.
    t0 = BASE_DAY + timedelta(minutes=10)
    start_interval(db, session.id, at=t0)
    end_interval(db, session.id, at=t0 + timedelta(minutes=25))

    # Enforced break, then a second (shorter) interval.
    t1 = t0 + timedelta(minutes=31)
    start_interval(db, session.id, at=t1)
    end_interval(db, session.id, at=t1 + timedelta(minutes=10))

    assert session.work_seconds == 35 * 60


def test_interval_accounting_survives_reload_between_requests(db, seed):
    # Each phase transition arrives as its own HTTP request, so the open
    # interval's start time round-trips through SQLite (which drops tzinfo).
    subj = seed.subject()
    session = start_study_session(db, seed.user.id, subj.id)
    start_interval(db, session.id, at=BASE_DAY)
    db.expire_all()
    end_interval(db, session.id, at=BASE_DAY + timedelta(minutes=25))
    assert db.get(StudySession, session.id).work_seconds == 25 * 60


def test_interval_calls_out_of_order_are_rejected(db, seed):
    subj = seed.subject()
    session = start_study_session(db, seed.user.id, subj.id)

    with pytest.raises(ValueError):
        end_interval(db, session.id, at=BASE_DAY)  # nothing open yet

    start_interval(db, session.id, at=BASE_DAY)
    with pytest.raises(ValueError):
        start_interval(db, session.id, at=BASE_DAY)  # already open


def test_transcript_persists_server_side_in_order(db, seed):
    subj = seed.subject()
    session = start_study_session(db, seed.user.id, subj.id)

    append_message(db, session.id, "assistant", "What do you already know?")
    append_message(db, session.id, "user", "Only the basics of matrices.")
    append_message(db, session.id, "assistant", "Let's start from there.")
    db.expire_all()

    transcript = get_transcript(db, session.id)
    assert [(m.role, m.content) for m in transcript] == [
        ("assistant", "What do you already know?"),
        ("user", "Only the basics of matrices."),
        ("assistant", "Let's start from there."),
    ]
    assert all(m.created_at is not None for m in transcript)


def test_append_message_rejects_unknown_role(db, seed):
    subj = seed.subject()
    session = start_study_session(db, seed.user.id, subj.id)
    with pytest.raises(ValueError):
        append_message(db, session.id, "system", "not a transcript role")


def test_notes_persist_across_reload(db, seed):
    subj = seed.subject()
    session = start_study_session(db, seed.user.id, subj.id)

    save_notes(db, session.id, "eigenvalues scale eigenvectors")
    db.expire_all()
    assert db.get(StudySession, session.id).notes == "eigenvalues scale eigenvectors"

    # Later saves overwrite (the panel owns the whole text).
    save_notes(db, session.id, "eigenvalues scale eigenvectors; det = product")
    db.expire_all()
    assert db.get(StudySession, session.id).notes == (
        "eigenvalues scale eigenvectors; det = product"
    )


def test_end_session_records_recap_and_closes_open_interval(db, seed):
    subj = seed.subject()
    session = start_study_session(db, seed.user.id, subj.id)
    start_interval(db, session.id, at=BASE_DAY)
    # User ends the session mid-interval; the open interval is credited to end.
    ended = end_study_session(
        db, session.id, wind_down_recap="Got eigenvalues; shaky on diagonalization.",
        at=BASE_DAY + timedelta(minutes=20),
    )

    assert ended.ended_at is not None
    assert ended.interval_started_at is None
    assert ended.work_seconds == 20 * 60
    assert ended.wind_down_recap == "Got eigenvalues; shaky on diagonalization."
