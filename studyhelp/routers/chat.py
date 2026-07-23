"""Chat endpoint for the LLM tutor."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession, joinedload

from ..database import get_db
from ..models import FSRSState, Item, Rating, ReviewSource, Subject, Topic, User
from ..scheduler import get_predicted_recall
from ..session import submit_review
from ..tutor import chat, parse_eval

router = APIRouter(prefix="/users/{user_id}/chat", tags=["chat"])


class ChatRequest(BaseModel):
    subject_id: int
    topic_id: int | None = None
    session_id: int | None = None
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


class ChatResponse(BaseModel):
    reply: str
    eval_data: dict | None = None


def _get_due_items(db: DBSession, user_id: int, subject_id: int,
                   topic_id: int | None) -> list[dict]:
    """Fetch due review items for context."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    q = (
        select(Item)
        .join(Topic)
        .where(
            Topic.subject_id == subject_id,
            Item.fsrs_state != FSRSState.NEW,
            Item.fsrs_due <= now,
        )
        .options(joinedload(Item.topic))
        .order_by(Item.fsrs_due)
        .limit(10)
    )

    if topic_id:
        q = q.where(Item.topic_id == topic_id)

    items = list(db.scalars(q).unique())

    # Also get some new items if there aren't enough due reviews
    if len(items) < 5:
        new_q = (
            select(Item)
            .join(Topic)
            .where(
                Topic.subject_id == subject_id,
                Item.fsrs_state == FSRSState.NEW,
            )
            .options(joinedload(Item.topic))
            .order_by(Item.created_at)
            .limit(5 - len(items))
        )
        if topic_id:
            new_q = new_q.where(Item.topic_id == topic_id)
        items.extend(list(db.scalars(new_q).unique()))

    return [
        {
            "id": item.id,
            "type": item.type.value,
            "front": item.front,
            "back": item.back,
            "topic": item.topic.name,
        }
        for item in items
    ]


@router.post("", response_model=ChatResponse)
def send_message(
    user_id: int,
    body: ChatRequest,
    db: DBSession = Depends(get_db),
):
    """Send a message to the tutor and get a response."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    subject = db.get(Subject, body.subject_id)
    if not subject:
        raise HTTPException(404, "Subject not found")

    topic_name = None
    if body.topic_id:
        topic = db.get(Topic, body.topic_id)
        if topic:
            topic_name = topic.name

    due_items = _get_due_items(db, user_id, body.subject_id, body.topic_id)

    try:
        raw_reply = chat(
            messages=body.messages,
            course_name=subject.name,
            topic_name=topic_name,
            due_items=due_items,
        )
    except Exception as e:
        raise HTTPException(502, f"LLM error: {str(e)}")

    clean_reply, eval_data = parse_eval(raw_reply)

    # If the tutor evaluated a response, try to log it against a matching item
    if eval_data and body.session_id and due_items:
        _try_log_review(db, user_id, body.session_id, due_items, eval_data)

    return ChatResponse(reply=clean_reply, eval_data=eval_data)


def _try_log_review(db: DBSession, user_id: int, session_id: int,
                    due_items: list[dict], eval_data: dict):
    """Best-effort: log the tutor's evaluation as an FSRS review."""
    rating_str = eval_data.get("rating", "").upper()
    rating_map = {"AGAIN": Rating.AGAIN, "HARD": Rating.HARD,
                  "GOOD": Rating.GOOD, "EASY": Rating.EASY}
    rating = rating_map.get(rating_str)
    if not rating:
        return

    was_correct = eval_data.get("was_correct", rating_str != "AGAIN")

    # Use the first due item as the reviewed item (best approximation).
    # Tagged CHAT: the outcome may belong to a different item than the one whose
    # prediction we store, so these are excluded from calibration (ADR-0001).
    if due_items:
        try:
            submit_review(
                db, user_id, session_id, due_items[0]["id"],
                rating, was_correct, source=ReviewSource.CHAT,
            )
        except (ValueError, Exception):
            pass
