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

from ..classification import classify_and_file
from ..database import get_db
from ..models import StudySession
from ..schemas import (
    CardDraft,
    CardDraftList,
    ClassifiedItemCreate,
    ItemOut,
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
    get_subject_memory,
    get_transcript,
    recent_summaries,
    rewrite_subject_memory,
    save_notes,
    start_interval,
    start_study_session,
    store_summary,
)
from ..tutor import (
    STUDY_PHASES,
    classify_item,
    generate_drafts,
    generate_summary_and_memory,
    study_chat,
)

router = APIRouter(prefix="/users/{user_id}/study-sessions", tags=["study"])


def _owned_session(db: DBSession, user_id: int, session_id: int) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(404, "Study session not found")
    return session


def _transcript_dicts(session: StudySession) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in session.messages]


def _summaries_text(db: DBSession, user_id: int, subject_id: int) -> list[str]:
    return [s.summary for s in recent_summaries(db, user_id, subject_id, limit=3)
            if s.summary]


@router.post("", response_model=StudySessionOut, status_code=201)
def start(user_id: int, body: StudySessionStart, db: DBSession = Depends(get_db)):
    """Create a study session and generate the tutor's level-check opener."""
    try:
        session = start_study_session(db, user_id, body.subject_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    memory = get_subject_memory(db, user_id, session.subject_id)
    summaries = _summaries_text(db, user_id, session.subject_id)
    try:
        opener = study_chat(
            phase="level_check", subject_name=session.subject.name, messages=[],
            subject_memory=memory, recent_summaries=summaries,
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
    memory = get_subject_memory(db, user_id, session.subject_id)
    summaries = _summaries_text(db, user_id, session.subject_id)

    try:
        reply = study_chat(
            phase=body.phase,
            subject_name=session.subject.name,
            messages=transcript,
            subject_memory=memory,
            recent_summaries=summaries,
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
    """End the session (crediting any open interval, storing the recap), then
    write the LLM session summary and rewrite the subject memory (ADR-0004).
    If the summary call fails the session still ends; the summary just stays
    null and the student can review the transcript."""
    session = _owned_session(db, user_id, session_id)
    try:
        session = end_study_session(db, session_id, wind_down_recap=body.wind_down_recap)
    except ValueError as e:
        raise HTTPException(409, str(e))

    transcript = "\n".join(f"{m.role}: {m.content}" for m in session.messages)
    prior_memory = get_subject_memory(db, user_id, session.subject_id)
    try:
        result = generate_summary_and_memory(
            transcript, session.notes, session.wind_down_recap, prior_memory
        )
        store_summary(db, session_id, result["summary"])
        rewrite_subject_memory(db, user_id, session.subject_id, result["memory"])
    except Exception:
        pass  # session is ended regardless; summary/memory are best-effort

    db.refresh(session)
    return session


@router.post("/{session_id}/drafts", response_model=CardDraftList)
def drafts(user_id: int, session_id: int, db: DBSession = Depends(get_db)):
    """Propose card drafts from the session's notes and summary (ephemeral)."""
    session = _owned_session(db, user_id, session_id)
    try:
        proposed = generate_drafts(session.notes, session.summary or "")
    except Exception as e:
        raise HTTPException(502, f"LLM error: {e}")
    return CardDraftList(drafts=[CardDraft(**d) for d in proposed])


@router.post("/{session_id}/drafts/accept", response_model=ItemOut, status_code=201)
def accept_draft(
    user_id: int, session_id: int, body: ClassifiedItemCreate,
    db: DBSession = Depends(get_db),
):
    """Accept an (edited) draft: classify it into a topic and add it to the deck."""
    session = _owned_session(db, user_id, session_id)
    item = classify_and_file(
        db, session.subject_id, body.front, body.back, classify_item,
        item_type=body.type, worked_steps=body.worked_steps,
    )
    return ItemOut.from_item(item)


@router.get("/{session_id}", response_model=StudySessionOut)
def get(user_id: int, session_id: int, db: DBSession = Depends(get_db)):
    """Fetch a study session with its persisted transcript and notes."""
    session = _owned_session(db, user_id, session_id)
    get_transcript(db, session_id)  # ensures messages are loaded
    return session
