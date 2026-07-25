"""Study-session service (issue #7, ADR-0004).

Lifecycle of the phased study session: level check → work intervals (each
closed by a reflection) → wind-down. The client owns the timer and reports
phase transitions; this module accumulates work-interval seconds from explicit
interval start/end calls — level-check and break time are never counted — and
persists the chat transcript and notes server-side. No FSRS reviews are
written from here.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import StudyChatMessage, StudySession, Subject, SubjectMemory, User

# Subject memory is a sharp picture, not a growing log: capped so it stays small
# enough to prepend to every tutor call. Prompted as a budget, enforced here by
# truncation as a hard guard.
MEMORY_CHAR_CAP = 4000


def _aware(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip; stored datetimes are UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _get_session(db: Session, session_id: int) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None:
        raise ValueError(f"Study session {session_id} not found")
    return session


def start_study_session(db: Session, user_id: int, subject_id: int) -> StudySession:
    if db.get(User, user_id) is None:
        raise ValueError(f"User {user_id} not found")
    subject = db.get(Subject, subject_id)
    if subject is None or subject.user_id != user_id:
        raise ValueError(f"Subject {subject_id} not found for user {user_id}")

    session = StudySession(user_id=user_id, subject_id=subject_id)
    db.add(session)
    db.commit()
    return session


def append_message(db: Session, session_id: int, role: str, content: str) -> StudyChatMessage:
    session = _get_session(db, session_id)
    if role not in ("user", "assistant"):
        raise ValueError(f"Invalid transcript role: {role}")
    message = StudyChatMessage(session_id=session.id, role=role, content=content)
    db.add(message)
    db.commit()
    return message


def get_transcript(db: Session, session_id: int) -> list[StudyChatMessage]:
    return _get_session(db, session_id).messages


def start_interval(db: Session, session_id: int, at: datetime | None = None) -> StudySession:
    session = _get_session(db, session_id)
    if session.ended_at is not None:
        raise ValueError("Session has ended")
    if session.interval_started_at is not None:
        raise ValueError("A work interval is already open")
    session.interval_started_at = at or datetime.now(timezone.utc)
    db.commit()
    return session


def _credit_open_interval(session: StudySession, now: datetime) -> None:
    """Add the open interval's elapsed seconds to the running total, if any."""
    if session.interval_started_at is None:
        return
    elapsed = (now - _aware(session.interval_started_at)).total_seconds()
    session.work_seconds += max(0, int(elapsed))
    session.interval_started_at = None


def end_interval(db: Session, session_id: int, at: datetime | None = None) -> StudySession:
    session = _get_session(db, session_id)
    if session.interval_started_at is None:
        raise ValueError("No work interval is open")
    _credit_open_interval(session, at or datetime.now(timezone.utc))
    db.commit()
    return session


def save_notes(db: Session, session_id: int, notes: str) -> StudySession:
    """Overwrite the session's notes (the panel owns the full text)."""
    session = _get_session(db, session_id)
    session.notes = notes
    db.commit()
    return session


def end_study_session(
    db: Session, session_id: int, wind_down_recap: str = "", at: datetime | None = None
) -> StudySession:
    """Close the session, crediting any open work interval and storing the
    user's wind-down recap. Guarded so a session ends once."""
    session = _get_session(db, session_id)
    if session.ended_at is not None:
        raise ValueError("Session has already ended")
    now = at or datetime.now(timezone.utc)
    _credit_open_interval(session, now)
    session.wind_down_recap = wind_down_recap
    session.ended_at = now
    db.commit()
    return session


# ── Session summary + subject memory (ADR-0004, stories 13-17) ───────────

def store_summary(db: Session, session_id: int, summary: str) -> StudySession:
    """Persist the LLM-written summary on a (usually just-ended) session."""
    session = _get_session(db, session_id)
    session.summary = summary
    db.commit()
    return session


def recent_summaries(
    db: Session, user_id: int, subject_id: int, limit: int = 5
) -> list[StudySession]:
    """Finished study sessions for a subject, newest first — what was covered
    lately (only those that have a summary)."""
    return list(db.scalars(
        select(StudySession)
        .where(
            StudySession.user_id == user_id,
            StudySession.subject_id == subject_id,
            StudySession.summary.is_not(None),
        )
        .order_by(StudySession.started_at.desc())
        .limit(limit)
    ))


def get_subject_memory(db: Session, user_id: int, subject_id: int) -> str:
    """The tutor's current running notes on the student for this subject, or ""."""
    mem = _find_memory(db, user_id, subject_id)
    return mem.content if mem else ""


def rewrite_subject_memory(
    db: Session, user_id: int, subject_id: int, new_memory: str,
    now: datetime | None = None,
) -> SubjectMemory:
    """Replace the subject memory wholesale (never append), capped in length."""
    now = now or datetime.now(timezone.utc)
    mem = _find_memory(db, user_id, subject_id)
    if mem is None:
        mem = SubjectMemory(user_id=user_id, subject_id=subject_id)
        db.add(mem)
    mem.content = new_memory[:MEMORY_CHAR_CAP]
    mem.updated_at = now
    db.commit()
    return mem


def _find_memory(db: Session, user_id: int, subject_id: int) -> SubjectMemory | None:
    return db.scalar(
        select(SubjectMemory).where(
            SubjectMemory.user_id == user_id,
            SubjectMemory.subject_id == subject_id,
        )
    )
