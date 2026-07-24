"""Daily session flow (Section 5.3).

Builds the queue, manages the session lifecycle, and handles fading
of worked examples based on item competence.
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
    ReviewSource,
    StudySession,
    Topic,
    User,
)
from .scheduler import get_predicted_recall, review_item
from .schemas import QueueItem, SessionQueue


def _steps_to_reveal(item: Item) -> int | None:
    """Determine how many worked-example steps to show (fading ladder).

    Full steps for new/learning items, fewer as stability grows.
    Section 5.2: 100% -> 50% -> 0% as competence rises.
    """
    if item.type != ItemType.WORKED_EXAMPLE or not item.worked_steps:
        return None

    total = len(item.worked_steps)
    if item.fsrs_state == FSRSState.NEW:
        return total  # show all steps

    stability = item.fsrs_stability or 0
    if stability < 5:
        return total  # still learning, show all
    elif stability < 30:
        return max(1, total // 2)  # show ~half
    else:
        return 0  # mastered: blank problem, reproduce from scratch


def get_due_counts(db: Session, user_id: int) -> dict:
    """Return counts of due reviews and available new items without creating a session."""
    now = datetime.now(timezone.utc)
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    due_count = len(list(db.scalars(
        select(Item.id)
        .join(Topic)
        .where(
            Topic.subject.has(user_id=user_id),
            Item.fsrs_state != FSRSState.NEW,
            Item.fsrs_due <= now,
        )
        .limit(user.daily_review_limit)
    )))

    new_count = len(list(db.scalars(
        select(Item.id)
        .join(Topic)
        .where(
            Topic.subject.has(user_id=user_id),
            Item.fsrs_state == FSRSState.NEW,
        )
        .limit(user.daily_new_limit)
    )))

    return {"reviews_due": due_count, "new_available": new_count}


def build_session_queue(db: Session, user_id: int) -> SessionQueue:
    """Build today's study queue per Section 5.3 step 1-2."""
    now = datetime.now(timezone.utc)

    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    # 1. Gather due reviews
    due_reviews_q = (
        select(Item)
        .join(Topic)
        .where(
            Topic.subject.has(user_id=user_id),
            Item.fsrs_state != FSRSState.NEW,
            Item.fsrs_due <= now,
        )
        .options(joinedload(Item.topic).joinedload(Topic.subject))
        .order_by(Item.fsrs_due)
        .limit(user.daily_review_limit)
    )
    due_reviews = list(db.scalars(due_reviews_q).unique())

    # 2. Gather new items (prereqs: parent topic items must not be NEW)
    new_items_q = (
        select(Item)
        .join(Topic)
        .where(
            Topic.subject.has(user_id=user_id),
            Item.fsrs_state == FSRSState.NEW,
        )
        .options(joinedload(Item.topic).joinedload(Topic.subject))
        .order_by(Item.created_at)
        .limit(user.daily_new_limit)
    )
    new_items = list(db.scalars(new_items_q).unique())

    # 3. Combine and interleave
    all_items = due_reviews + new_items
    interleaved = interleave(all_items)

    # 4. Create session record
    session = StudySession(
        user_id=user_id,
        new_count=len(new_items),
        review_count=len(due_reviews),
    )
    db.add(session)
    db.flush()

    # 5. Build queue items for the API
    queue_items = []
    for item in interleaved:
        predicted = get_predicted_recall(item, now)
        queue_items.append(
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
                predicted_recall=predicted,
                steps_to_reveal=_steps_to_reveal(item),
            )
        )

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
    session_id: int,
    item_id: int,
    rating: Rating,
    was_correct: bool,
    response_ms: int | None = None,
    source: ReviewSource = ReviewSource.CARD,
) -> Review:
    """Process a single review within a session (Section 5.3 step 3e-f).

    `source` records where the rating came from (CARD = card-player, CHAT =
    tutor). Every review written here has its prediction and outcome referring to
    the same `item_id` — the card path passes the reviewed item, and the chat path
    only calls this after resolving the item actually quizzed — so it is marked
    `attribution_exact` and is trustworthy for calibration. See ADR-0003.
    """
    now = datetime.now(timezone.utc)
    item = db.get(Item, item_id)
    if item is None:
        raise ValueError(f"Item {item_id} not found")

    user = db.get(User, user_id)
    predicted = get_predicted_recall(item, now)

    # Log the review (append-only)
    review = Review(
        item_id=item_id,
        user_id=user_id,
        rating_given=rating,
        predicted_recall=predicted,
        was_correct=was_correct,
        response_ms=response_ms,
        source=source,
        attribution_exact=True,
        reviewed_at=now,
    )
    db.add(review)

    # Update FSRS state on the item
    review_item(item, rating, target_retention=user.target_retention, now=now)

    # Update session counters
    session = db.get(StudySession, session_id)
    if session:
        session.items_seen = (session.items_seen or 0) + 1

    db.commit()
    return review


def end_session(db: Session, session_id: int) -> StudySession:
    """Close a session and compute calibration error."""
    session = db.get(StudySession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    session.ended_at = datetime.now(timezone.utc)

    # Compute average calibration error: |predicted_recall - actual|
    reviews = list(
        db.scalars(
            select(Review).where(
                Review.reviewed_at >= session.started_at,
                Review.user_id == session.user_id,
            )
        )
    )

    calibration_errors = []
    for r in reviews:
        if r.predicted_recall is not None:
            actual = 1.0 if r.was_correct else 0.0
            calibration_errors.append(abs(r.predicted_recall - actual))

    if calibration_errors:
        session.avg_calibration_error = sum(calibration_errors) / len(calibration_errors)

    db.commit()
    return session
