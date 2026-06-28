from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..schemas import ReviewCreate, ReviewOut, SessionOut, SessionQueue
from ..session import build_session_queue, end_session, get_due_counts, submit_review

router = APIRouter(prefix="/users/{user_id}/sessions", tags=["sessions"])


@router.get("/due")
def due_counts(user_id: int, db: DBSession = Depends(get_db)):
    """Get due review and new item counts without creating a session."""
    try:
        return get_due_counts(db, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("", response_model=SessionQueue, status_code=201)
def start_session(user_id: int, db: DBSession = Depends(get_db)):
    """Build today's interleaved study queue and start a new session."""
    try:
        return build_session_queue(db, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{session_id}/reviews/{item_id}", response_model=ReviewOut)
def review_item(
    user_id: int,
    session_id: int,
    item_id: int,
    body: ReviewCreate,
    db: DBSession = Depends(get_db),
):
    """Submit a review for an item within a session."""
    try:
        review = submit_review(
            db,
            user_id=user_id,
            session_id=session_id,
            item_id=item_id,
            rating=body.rating,
            was_correct=body.was_correct,
            response_ms=body.response_ms,
        )
        return review
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{session_id}/end", response_model=SessionOut)
def end(user_id: int, session_id: int, db: DBSession = Depends(get_db)):
    """End a session and compute calibration stats."""
    try:
        return end_session(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/{session_id}/reveal/{item_id}")
def reveal_answer(
    user_id: int, session_id: int, item_id: int, db: DBSession = Depends(get_db)
):
    """Reveal the answer/solution for an item (after retrieval attempt)."""
    from ..models import Item

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return {
        "back": item.back,
        "worked_steps": item.worked_steps,
    }
