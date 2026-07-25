"""FSRS scheduling engine wrapping py-fsrs v6 (Section 5.4).

Translates between our Item model's FSRS fields and the py-fsrs Card/Rating
objects. All scheduling math comes from the library.
"""

from datetime import datetime, timezone

from fsrs import Card, Rating as FSRSRating, Scheduler, State

from .models import FSRSState, Item, Rating

# Map our Rating enum to py-fsrs Rating enum
_RATING_MAP: dict[Rating, FSRSRating] = {
    Rating.AGAIN: FSRSRating.Again,
    Rating.HARD: FSRSRating.Hard,
    Rating.GOOD: FSRSRating.Good,
    Rating.EASY: FSRSRating.Easy,
}

_STATE_TO_FSRS: dict[FSRSState, State] = {
    FSRSState.LEARNING: State.Learning,
    FSRSState.REVIEW: State.Review,
    FSRSState.RELEARNING: State.Relearning,
}

_STATE_FROM_FSRS: dict[State, FSRSState] = {v: k for k, v in _STATE_TO_FSRS.items()}


def _as_utc(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; py-fsrs requires aware UTC ones."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _card_from_item(item: Item) -> Card:
    """Reconstruct a py-fsrs Card from an Item's persisted FSRS fields."""
    card = Card()
    if item.fsrs_state != FSRSState.NEW and item.fsrs_last_review is not None:
        card.stability = item.fsrs_stability
        card.difficulty = item.fsrs_difficulty
        card.due = _as_utc(item.fsrs_due) or datetime.now(timezone.utc)
        card.last_review = _as_utc(item.fsrs_last_review)
        card.step = item.fsrs_step
        card.state = _STATE_TO_FSRS.get(item.fsrs_state, State.Learning)
    return card


def _persist_card(item: Item, card: Card) -> None:
    """Write py-fsrs Card state back onto an Item."""
    item.fsrs_stability = card.stability
    item.fsrs_difficulty = card.difficulty
    item.fsrs_due = card.due
    item.fsrs_last_review = card.last_review
    item.fsrs_step = card.step
    item.fsrs_state = _STATE_FROM_FSRS.get(card.state, FSRSState.LEARNING)


def get_predicted_recall(item: Item, now: datetime | None = None) -> float | None:
    """Return the current predicted recall probability for an item."""
    if item.fsrs_state == FSRSState.NEW or item.fsrs_stability is None:
        return None
    now = now or datetime.now(timezone.utc)
    scheduler = Scheduler()
    card = _card_from_item(item)
    return scheduler.get_card_retrievability(card, now)


def review_item(
    item: Item,
    rating: Rating,
    target_retention: float = 0.90,
    now: datetime | None = None,
) -> None:
    """Process a review: update the Item's FSRS fields in-place.

    Call this after the user rates an item. The item must be flushed/committed
    by the caller.
    """
    now = now or datetime.now(timezone.utc)
    scheduler = Scheduler()
    scheduler.desired_retention = target_retention

    card = _card_from_item(item)
    card, _ = scheduler.review_card(card, _RATING_MAP[rating], now)
    _persist_card(item, card)
