"""Tests for review submission.

Every review written through submit_review pairs its prediction and outcome on
the item it is given, so it must carry the attribution_exact trust flag that
calibration filters on (ADR-0003).
"""

from studyhelp.models import Rating, Review, ReviewSource
from studyhelp.session import submit_review


def test_submit_review_marks_review_attribution_exact(db, seed):
    subj = seed.subject()

    review = submit_review(
        db, seed.user.id, session_id=999, item_id=subj._seed_item_id,
        rating=Rating.GOOD, was_correct=True, source=ReviewSource.CHAT,
    )

    assert review.attribution_exact is True
    # and it is what actually landed in the DB, not just the returned object
    stored = db.get(Review, review.id)
    assert stored.attribution_exact is True
    # NB: predicted_recall is still None here — the seeded item is NEW, so there
    # is no FSRS state to predict from. Such a review is exact but not
    # trustworthy, since trust requires both the flag and a non-null prediction.
    assert stored.predicted_recall is None
