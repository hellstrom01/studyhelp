"""Shared test fixtures.

Stands up an in-memory SQLite database and a small seeding helper so features
can be tested against real ORM rows without touching the web or LLM layers.
This is the prior art for future tests (see the calibration dashboard spec).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from studyhelp.database import Base
from studyhelp.models import (
    Item,
    ItemType,
    Rating,
    Review,
    ReviewSource,
    Subject,
    SubjectType,
    Topic,
    User,
)

# A fixed reference instant so trend-by-day tests are deterministic.
BASE_DAY = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    """A fresh in-memory database session per test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class Seeder:
    """Ergonomic helper to build the user → subject → topic → item chain and
    attach reviews with explicit predicted_recall / correctness / source / time.
    """

    def __init__(self, db):
        self.db = db
        self.user = User(display_name="Tester")
        db.add(self.user)
        db.flush()

    def subject(self, name="Subject"):
        subj = Subject(user_id=self.user.id, name=name, type=SubjectType.MATH)
        self.db.add(subj)
        self.db.flush()
        topic = Topic(subject_id=subj.id, name="Topic")
        self.db.add(topic)
        self.db.flush()
        item = Item(topic_id=topic.id, type=ItemType.CONCEPT_QA, front="q", back="a")
        self.db.add(item)
        self.db.flush()
        # stash the item so add() can hang reviews off this subject
        subj._seed_item_id = item.id
        return subj

    def add(self, subject, predicted, correct, source=ReviewSource.CARD, when=None,
            attribution_exact=None):
        # Default the trust flag to match the source when not given explicitly:
        # CARD reviews are exact by construction; other sources are not unless said so.
        if attribution_exact is None:
            attribution_exact = source == ReviewSource.CARD
        review = Review(
            item_id=subject._seed_item_id,
            user_id=self.user.id,
            rating_given=Rating.GOOD if correct else Rating.AGAIN,
            predicted_recall=predicted,
            was_correct=correct,
            source=source,
            attribution_exact=attribution_exact,
            reviewed_at=when or BASE_DAY,
        )
        self.db.add(review)
        self.db.flush()
        return review

    def add_many(self, subject, predicted, n_correct, n_wrong, **kw):
        for _ in range(n_correct):
            self.add(subject, predicted, True, **kw)
        for _ in range(n_wrong):
            self.add(subject, predicted, False, **kw)


@pytest.fixture
def seed(db):
    return Seeder(db)
