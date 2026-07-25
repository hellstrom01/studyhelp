"""Review-session API (ADR-0004: the retrieval-practice mode).

Due items one at a time, the user types an answer, gets LLM commentary, and
rates their own attempt. The self-assessment — never the LLM — writes the Review
row, exactly attributed by construction.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ..commentary import comment_on_attempt
from ..database import get_db
from ..models import Item
from ..review import (
    end_review_session,
    get_due_counts,
    start_review_session,
    submit_review,
)
from ..schemas import (
    CommentaryIn,
    CommentaryOut,
    RateIn,
    ReviewOut,
    ReviewSessionStart,
    SessionQueue,
)

router = APIRouter(prefix="/users/{user_id}/review-sessions", tags=["review"])


@router.get("/due")
def due_counts(
    user_id: int, subject_id: int | None = None, db: DBSession = Depends(get_db)
):
    """Due review and new-item counts, optionally scoped to a subject."""
    try:
        return get_due_counts(db, user_id, subject_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("", response_model=SessionQueue, status_code=201)
def start(user_id: int, body: ReviewSessionStart, db: DBSession = Depends(get_db)):
    """Start a review session; returns the interleaved due/new queue."""
    try:
        return start_review_session(db, user_id, body.subject_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{session_id}/commentary", response_model=CommentaryOut)
def commentary(
    user_id: int, session_id: int, body: CommentaryIn,
    db: DBSession = Depends(get_db),
):
    """LLM feedback on a typed attempt, plus the revealed answer. No rating."""
    item = db.get(Item, body.item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    try:
        text = comment_on_attempt(item.front, item.back, body.typed_answer)
    except Exception as e:
        raise HTTPException(502, f"LLM error: {str(e)}")
    return CommentaryOut(commentary=text, answer=item.back, worked_steps=item.worked_steps)


@router.post("/{session_id}/rate", response_model=ReviewOut)
def rate(
    user_id: int, session_id: int, body: RateIn, db: DBSession = Depends(get_db)
):
    """Record the user's self-assessment; drives FSRS and writes the Review row."""
    try:
        return submit_review(
            db, user_id, session_id, body.item_id, body.rating,
            typed_answer=body.typed_answer, commentary=body.commentary,
            response_ms=body.response_ms,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{session_id}/end", status_code=200)
def end(user_id: int, session_id: int, db: DBSession = Depends(get_db)):
    """End the review session; unanswered items simply stay due."""
    try:
        session = end_review_session(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"session_id": session.id, "items_reviewed": session.items_reviewed}
