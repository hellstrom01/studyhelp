"""Tests for the review-session service (the agreed service-function seam).

Review sessions are the only producer of new Review rows (ADR-0004): due items
are presented one at a time, the user types an answer, gets LLM commentary, and
rates themself — that self-assessment drives FSRS. Everything here is driven by
seeded ORM rows; no HTTP, no LLM.
"""

from datetime import timedelta

from studyhelp.models import (
    FSRSState,
    ItemType,
    Rating,
    ReviewSession,
    ReviewSource,
)
from studyhelp.review import (
    end_review_session,
    get_due_counts,
    start_review_session,
    submit_review,
)
from tests.conftest import BASE_DAY


def test_start_creates_record_and_queues_due_items(db, seed):
    subj = seed.subject()
    due1 = seed.item(subj, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=1))
    due2 = seed.item(subj, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=2))

    queue = start_review_session(db, seed.user.id)

    session = db.get(ReviewSession, queue.session_id)
    assert session is not None
    assert session.user_id == seed.user.id
    assert session.ended_at is None
    assert session.items_reviewed == 0

    queued_ids = {q.item_id for q in queue.items}
    assert due1.id in queued_ids
    assert due2.id in queued_ids


def test_rating_writes_exactly_attributed_card_review(db, seed):
    subj = seed.subject()
    item = seed.item(subj, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=1))
    queue = start_review_session(db, seed.user.id)

    review = submit_review(
        db, seed.user.id, queue.session_id, item.id, Rating.GOOD,
        typed_answer="my attempt", commentary="close, but note the sign",
    )

    assert review.source == ReviewSource.CARD
    assert review.attribution_exact is True
    assert review.review_session_id == queue.session_id
    assert review.typed_answer == "my attempt"
    assert review.commentary == "close, but note the sign"
    # predicted recall computed at rating time, before FSRS state moves
    assert review.predicted_recall is not None
    assert 0.0 <= review.predicted_recall <= 1.0
    # self-assessment "Got it" counts as a successful retrieval
    assert review.was_correct is True

    # the rating drives FSRS: the item is rescheduled into the future
    db.refresh(item)
    assert item.fsrs_due > review.reviewed_at

    session = db.get(ReviewSession, queue.session_id)
    assert session.items_reviewed == 1


def test_forgot_grade_is_an_unsuccessful_retrieval(db, seed):
    subj = seed.subject()
    item = seed.item(subj, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=1))
    queue = start_review_session(db, seed.user.id)

    review = submit_review(
        db, seed.user.id, queue.session_id, item.id, Rating.AGAIN,
        typed_answer="no idea",
    )

    assert review.was_correct is False
    assert review.rating_given == Rating.AGAIN


def test_new_item_review_has_no_prediction_but_is_still_exact(db, seed):
    # A never-reviewed item has no FSRS memory state, so no predicted recall —
    # the row is still exactly attributed (it just won't count for calibration).
    subj = seed.subject()
    item = seed.item(subj)  # NEW
    queue = start_review_session(db, seed.user.id)

    review = submit_review(
        db, seed.user.id, queue.session_id, item.id, Rating.GOOD,
        typed_answer="attempt",
    )

    assert review.predicted_recall is None
    assert review.attribution_exact is True
    db.refresh(item)
    assert item.fsrs_state != FSRSState.NEW


def test_new_items_backfill_the_queue_when_few_are_due(db, seed):
    subj = seed.subject()
    due = seed.item(subj, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=1))
    new1 = seed.item(subj)  # NEW
    new2 = seed.item(subj)  # NEW

    queue = start_review_session(db, seed.user.id, now=BASE_DAY)

    queued_ids = {q.item_id for q in queue.items}
    assert due.id in queued_ids
    assert new1.id in queued_ids
    assert new2.id in queued_ids
    assert queue.total_reviews == 1
    # new1, new2, and the subject's default seed item are all NEW
    assert queue.total_new == 3
    # new items are flagged so the client can present them as first-encounters
    assert {q.is_new for q in queue.items if q.item_id == new1.id} == {True}


def test_not_yet_due_items_are_not_queued(db, seed):
    subj = seed.subject()
    future = seed.item(subj, state=FSRSState.REVIEW, due=BASE_DAY + timedelta(days=5))

    queue = start_review_session(db, seed.user.id, now=BASE_DAY)

    assert future.id not in {q.item_id for q in queue.items}
    assert queue.total_reviews == 0


def test_worked_example_step_fading_survives_in_review(db, seed):
    subj = seed.subject()
    steps = ["s1", "s2", "s3", "s4"]
    # A new worked example shows all steps; a well-stabilised one shows none.
    new_we = seed.item(subj, type=ItemType.WORKED_EXAMPLE, steps=steps)
    mastered = seed.item(
        subj, type=ItemType.WORKED_EXAMPLE, steps=steps,
        state=FSRSState.REVIEW, stability=50.0, due=BASE_DAY - timedelta(days=1),
    )

    queue = start_review_session(db, seed.user.id)
    by_id = {q.item_id: q for q in queue.items}

    assert by_id[new_we.id].steps_to_reveal == 4
    assert by_id[mastered.id].steps_to_reveal == 0


def test_subject_scoped_queue_and_due_counts(db, seed):
    a = seed.subject("A")
    b = seed.subject("B")
    in_a = seed.item(a, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=1))
    in_b = seed.item(b, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=1))

    queue = start_review_session(db, seed.user.id, subject_id=a.id)
    queued_ids = {q.item_id for q in queue.items}
    assert in_a.id in queued_ids
    assert in_b.id not in queued_ids

    counts_a = get_due_counts(db, seed.user.id, subject_id=a.id)
    assert counts_a["reviews_due"] == 1  # only A's due item, plus A's seed NEW item
    assert counts_a["new_available"] == 1


def test_end_review_session_stamps_ended_at(db, seed):
    subj = seed.subject()
    seed.item(subj, state=FSRSState.REVIEW, due=BASE_DAY - timedelta(days=1))
    queue = start_review_session(db, seed.user.id)

    session = end_review_session(db, queue.session_id)

    assert session.ended_at is not None
    # ending is idempotent-safe: unanswered items simply stay due (nothing asserted
    # about the queue here — the point is the session closes cleanly)
