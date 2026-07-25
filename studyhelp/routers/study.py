"""Study-session endpoints (issue #7, ADR-0004).

The phased study session: an untimed level check gates the timer, work
intervals of Socratic tutor chat run with a notes panel alongside, and a
wind-down recap closes the session. The client owns the timer and reports phase
transitions and interval start/end; the server accumulates work-interval
seconds and persists the transcript, notes, and recap. No Review rows are
written here.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models import StudySession
from ..schemas import (
    StudyChatReply,
    StudyChatRequest,
    StudyEndRequest,
    StudyNotesUpdate,
    StudySessionOut,
    StudySessionStart,
)
from ..study import (
    append_message,
    end_interval,
    end_study_session,
    get_transcript,
    save_notes,
    start_interval,
    start_study_session,
)
from ..tutor import STUDY_PHASES, study_chat

router = APIRouter(prefix="/users/{user_id}/study-sessions", tags=["study"])


def _owned_session(db: DBSession, user_id: int, session_id: int) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(404, "Study session not found")
    return session


def _transcript_dicts(session: StudySession) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in session.messages]


@router.post("", response_model=StudySessionOut, status_code=201)
def start(user_id: int, body: StudySessionStart, db: DBSession = Depends(get_db)):
    """Create a study session and generate the tutor's level-check opener."""
    try:
        session = start_study_session(db, user_id, body.subject_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    try:
        opener = study_chat(
            phase="level_check", subject_name=session.subject.name, messages=[]
        )
    except Exception as e:
        raise HTTPException(502, f"LLM error: {e}")
    append_message(db, session.id, "assistant", opener)

    db.refresh(session)
    return session


@router.post("/{session_id}/messages", response_model=StudyChatReply)
def send_message(
    user_id: int, session_id: int, body: StudyChatRequest, db: DBSession = Depends(get_db)
):
    """Persist the student's message, get the tutor's reply, and persist it."""
    session = _owned_session(db, user_id, session_id)
    if body.phase not in STUDY_PHASES:
        raise HTTPException(422, f"Unknown study phase: {body.phase}")

    append_message(db, session.id, "user", body.content)
    transcript = _transcript_dicts(db.get(StudySession, session_id))

    try:
        reply = study_chat(
            phase=body.phase,
            subject_name=session.subject.name,
            messages=transcript,
        )
    except Exception as e:
        raise HTTPException(502, f"LLM error: {e}")

    append_message(db, session.id, "assistant", reply)
    return StudyChatReply(reply=reply)


@router.post("/{session_id}/interval/start", response_model=StudySessionOut)
def interval_start(user_id: int, session_id: int, db: DBSession = Depends(get_db)):
    """Mark the start of a work interval (the focus timer just started)."""
    _owned_session(db, user_id, session_id)
    try:
        session = start_interval(db, session_id)
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.refresh(session)
    return session


@router.post("/{session_id}/interval/end", response_model=StudySessionOut)
def interval_end(user_id: int, session_id: int, db: DBSession = Depends(get_db)):
    """Close the open work interval and credit its seconds (a break begins)."""
    _owned_session(db, user_id, session_id)
    try:
        session = end_interval(db, session_id)
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.refresh(session)
    return session


@router.put("/{session_id}/notes", response_model=StudySessionOut)
def put_notes(
    user_id: int, session_id: int, body: StudyNotesUpdate, db: DBSession = Depends(get_db)
):
    """Overwrite the session's notes (autosaved from the notes panel)."""
    _owned_session(db, user_id, session_id)
    session = save_notes(db, session_id, body.notes)
    db.refresh(session)
    return session


@router.post("/{session_id}/end", response_model=StudySessionOut)
def end(
    user_id: int, session_id: int, body: StudyEndRequest, db: DBSession = Depends(get_db)
):
    """End the session, crediting any open interval and storing the recap."""
    _owned_session(db, user_id, session_id)
    try:
        session = end_study_session(db, session_id, wind_down_recap=body.wind_down_recap)
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=StudySessionOut)
def get(user_id: int, session_id: int, db: DBSession = Depends(get_db)):
    """Fetch a study session with its persisted transcript and notes."""
    session = _owned_session(db, user_id, session_id)
    get_transcript(db, session_id)  # ensures messages are loaded
    return session
