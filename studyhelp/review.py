"""Review-session flow (ADR-0004: the retrieval-practice mode).

Review sessions are the only producer of new Review rows. Due items are
presented one at a time (interleaved, NEW-item backfilled), the user types an
answer and gets LLM commentary, then rates their own attempt — that
self-assessment, never the LLM, drives FSRS. Every row is source CARD and
exactly attributed by construction. Review sessions replaced the legacy
card-player flow, which has been retired (ADR-0004, #5).
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .interleaver import interleave
from .models import (
    FSRSState,
    Item,
    ItemType,
    Rating,
    Review,
    ReviewSession,
    ReviewSource,
    Topic,
    User,
)
from .scheduler import get_predicted_recall, review_item
from .schemas import QueueItem, SessionQueue


def _steps_to_reveal(item: Item) -> int | None:
    """How many worked-example steps to show (fading ladder): all when new/low
    stability, ~half at moderate stability, none once mastered (Section 5.2)."""
    if item.type != ItemType.WORKED_EXAMPLE or not item.worked_steps:
        return None
    total = len(item.worked_steps)
    if item.fsrs_state == FSRSState.NEW:
        return total
    stability = item.fsrs_stability or 0
    if stability < 5:
        return total
    elif stability < 30:
        return max(1, total // 2)
    return 0


def _due_items_query(user_id: int, subject_id: int | None, now: datetime):
    q = (
        select(Item)
        .join(Topic)
        .where(
            Topic.subject.has(user_id=user_id),
            Item.fsrs_state != FSRSState.NEW,
            Item.fsrs_due <= now,
        )
    )
    if subject_id is not None:
        q = q.where(Topic.subject_id == subject_id)
    return q


def _new_items_query(user_id: int, subject_id: int | None):
    q = (
        select(Item)
        .join(Topic)
        .where(
            Topic.subject.has(user_id=user_id),
            Item.fsrs_state == FSRSState.NEW,
        )
    )
    if subject_id is not None:
        q = q.where(Topic.subject_id == subject_id)
    return q


def get_due_counts(
    db: Session, user_id: int, subject_id: int | None = None,
    now: datetime | None = None,
) -> dict:
    """Counts of due reviews and available new items, optionally per subject."""
    now = now or datetime.now(timezone.utc)
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    due_count = len(list(db.scalars(
        _due_items_query(user_id, subject_id, now)
        .with_only_columns(Item.id).limit(user.daily_review_limit)
    )))
    new_count = len(list(db.scalars(
        _new_items_query(user_id, subject_id)
        .with_only_columns(Item.id).limit(user.daily_new_limit)
    )))
    return {"reviews_due": due_count, "new_available": new_count}


def start_review_session(
    db: Session, user_id: int, subject_id: int | None = None,
    now: datetime | None = None,
) -> SessionQueue:
    """Create a review session and build its interleaved queue: due items first,
    backfilled with never-reviewed items, interleaved across topics and types."""
    now = now or datetime.now(timezone.utc)
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    due_reviews = list(db.scalars(
        _due_items_query(user_id, subject_id, now)
        .options(joinedload(Item.topic).joinedload(Topic.subject))
        .order_by(Item.fsrs_due).limit(user.daily_review_limit)
    ).unique())
    new_items = list(db.scalars(
        _new_items_query(user_id, subject_id)
        .options(joinedload(Item.topic).joinedload(Topic.subject))
        .order_by(Item.created_at).limit(user.daily_new_limit)
    ).unique())

    interleaved = interleave(due_reviews + new_items)

    session = ReviewSession(user_id=user_id)
    db.add(session)
    db.flush()

    queue_items = [
        QueueItem(
            item_id=item.id,
            topic_id=item.topic_id,
            topic_name=item.topic.name,
            subject_name=item.topic.subject.name,
            type=item.type,
            front=item.front,
            worked_steps=item.worked_steps,
            diagram_url=item.diagram_url,
            is_new=(item.fsrs_state == FSRSState.NEW),
            predicted_recall=get_predicted_recall(item, now),
            steps_to_reveal=_steps_to_reveal(item),
        )
        for item in interleaved
    ]

    db.commit()
    return SessionQueue(
        session_id=session.id,
        items=queue_items,
        total_reviews=len(due_reviews),
        total_new=len(new_items),
    )


def submit_review(
    db: Session,
    user_id: int,
    review_session_id: int,
    item_id: int,
    rating: Rating,
    typed_answer: str | None = None,
    commentary: str | None = None,
    response_ms: int | None = None,
) -> Review:
    """Record the user's self-assessment of one retrieval attempt.

    The user's 4-grade rating — never the LLM's commentary — drives FSRS.
    Predicted recall is computed at rating time, before the item's state moves,
    and prediction and outcome refer to the same `item_id` by construction, so
    every row is source CARD and exactly attributed. AGAIN is the one
    unsuccessful-retrieval grade.
    """
    now = datetime.now(timezone.utc)
    item = db.get(Item, item_id)
    if item is None:
        raise ValueError(f"Item {item_id} not found")

    user = db.get(User, user_id)
    predicted = get_predicted_recall(item, now)

    review = Review(
        item_id=item_id,
        user_id=user_id,
        rating_given=rating,
        predicted_recall=predicted,
        was_correct=rating != Rating.AGAIN,
        response_ms=response_ms,
        source=ReviewSource.CARD,
        attribution_exact=True,
        review_session_id=review_session_id,
        typed_answer=typed_answer,
        commentary=commentary,
        reviewed_at=now,
    )
    db.add(review)

    review_item(item, rating, target_retention=user.target_retention, now=now)

    session = db.get(ReviewSession, review_session_id)
    if session:
        session.items_reviewed = (session.items_reviewed or 0) + 1

    db.commit()
    return review


def end_review_session(db: Session, review_session_id: int) -> ReviewSession:
    """Close a review session. Can be called at any point — unanswered items
    stay due and reappear in the next session's queue."""
    session = db.get(ReviewSession, review_session_id)
    if session is None:
        raise ValueError(f"Review session {review_session_id} not found")
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    return session
