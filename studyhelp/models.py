"""SQLAlchemy models mapping directly to the spec's data model (Section 5.1)."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


class SubjectType(str, enum.Enum):
    MATH = "MATH"
    CS = "CS"
    SCIENCE = "SCIENCE"
    OTHER = "OTHER"


class ItemType(str, enum.Enum):
    CONCEPT_QA = "CONCEPT_QA"
    THEOREM_TRIGGER = "THEOREM_TRIGGER"
    WORKED_EXAMPLE = "WORKED_EXAMPLE"
    PROBLEM_HIDDEN = "PROBLEM_HIDDEN"
    CODE_FROM_SCRATCH = "CODE_FROM_SCRATCH"
    FEYNMAN_PROMPT = "FEYNMAN_PROMPT"
    CLOZE = "CLOZE"


class Rating(str, enum.Enum):
    AGAIN = "AGAIN"
    HARD = "HARD"
    GOOD = "GOOD"
    EASY = "EASY"


class FSRSState(str, enum.Enum):
    NEW = "NEW"
    LEARNING = "LEARNING"
    REVIEW = "REVIEW"
    RELEARNING = "RELEARNING"


class ReviewSource(str, enum.Enum):
    """Where a review's rating originated: CARD (card-player flow) or CHAT (tutor
    chat). This records provenance and feeds the coverage counts; trust for
    calibration is carried separately by `Review.attribution_exact`. Both sources
    can be trustworthy now that chat outcomes are attributed to the item actually
    quizzed. See ADR-0001 and ADR-0003.
    """
    CARD = "CARD"
    CHAT = "CHAT"


class BiasLabel(str, enum.Enum):
    """Plain-language reading of calibration bias (closed set, per CONTEXT.md)."""
    OVERCONFIDENT = "overconfident"
    UNDERCONFIDENT = "underconfident"
    WELL_CALIBRATED = "well calibrated"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── User ─────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    target_retention: Mapped[float] = mapped_column(Float, default=0.90)
    daily_new_limit: Mapped[int] = mapped_column(Integer, default=20)
    daily_review_limit: Mapped[int] = mapped_column(Integer, default=100)
    pomodoro_focus_min: Mapped[int] = mapped_column(Integer, default=25)
    break_min: Mapped[int] = mapped_column(Integer, default=5)
    sleep_reminder_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "22:30"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    subjects: Mapped[list["Subject"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ── Subject ──────────────────────────────────────────────────────────────

class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[SubjectType] = mapped_column(Enum(SubjectType))
    color: Mapped[str] = mapped_column(String(7), default="#4A90D9")

    user: Mapped["User"] = relationship(back_populates="subjects")
    topics: Mapped[list["Topic"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


# ── Topic ────────────────────────────────────────────────────────────────

class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    name: Mapped[str] = mapped_column(String(200))
    parent_topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    parent: Mapped["Topic | None"] = relationship(remote_side=[id])
    items: Mapped[list["Item"]] = relationship(back_populates="topic", cascade="all, delete-orphan")


# ── Item ─────────────────────────────────────────────────────────────────

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    type: Mapped[ItemType] = mapped_column(Enum(ItemType))
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text, default="")
    worked_steps: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ordered list of step strings
    diagram_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    difficulty_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # FSRS memory state (matches py-fsrs v6 Card fields)
    fsrs_stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    fsrs_difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    fsrs_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fsrs_last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fsrs_step: Mapped[int] = mapped_column(Integer, default=0)
    fsrs_state: Mapped[FSRSState] = mapped_column(Enum(FSRSState), default=FSRSState.NEW)

    topic: Mapped["Topic"] = relationship(back_populates="items")
    reviews: Mapped[list["Review"]] = relationship(back_populates="item", cascade="all, delete-orphan")


# ── Review ───────────────────────────────────────────────────────────────

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating_given: Mapped[Rating] = mapped_column(Enum(Rating))
    predicted_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[ReviewSource] = mapped_column(Enum(ReviewSource), default=ReviewSource.CARD)
    # True when the prediction and outcome provably refer to the same item, so
    # this review is trustworthy for calibration: always for CARD reviews, and
    # for CHAT reviews whose outcome was resolved to the item actually quizzed.
    # Legacy chat rows written before attribution was fixed are null/false and
    # stay excluded. Carries the trust decision; `source` still records provenance.
    # See ADR-0003.
    attribution_exact: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    item: Mapped["Item"] = relationship(back_populates="reviews")


# ── Legacy session (card-player flow) ────────────────────────────────────

class LegacySession(Base):
    """Session record for the legacy card-player flow. The phased study session
    (ADR-0004) is `StudySession` below; this model is retired by issue #11.
    """
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    pomodoros_completed: Mapped[int] = mapped_column(Integer, default=0)
    avg_calibration_error: Mapped[float | None] = mapped_column(Float, nullable=True)


# ── Study session (phased encoding mode, ADR-0004) ───────────────────────

class StudySession(Base):
    """One phased study session: level check → work intervals (each closed by a
    reflection) → wind-down. Produces no Review rows. The client owns the timer
    and reports phase transitions; the server accumulates work-interval seconds
    from explicit interval start/end calls, so level-check and break time are
    never counted.
    """
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_seconds: Mapped[int] = mapped_column(Integer, default=0)
    # Start of the currently open work interval; null outside intervals.
    interval_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    # The user's own wind-down recap, captured when the session ends. Distinct
    # from the LLM-written session summary (issue #9), which lands here later.
    wind_down_recap: Mapped[str] = mapped_column(Text, default="")

    subject: Mapped["Subject"] = relationship()
    messages: Mapped[list["StudyChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        order_by="StudyChatMessage.id",
    )


class StudyChatMessage(Base):
    """One turn of a study session's tutor chat, persisted server-side."""
    __tablename__ = "study_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("study_sessions.id"))
    role: Mapped[str] = mapped_column(String(9))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["StudySession"] = relationship(back_populates="messages")


# ── ExplanationLog ───────────────────────────────────────────────────────

class ExplanationLog(Base):
    __tablename__ = "explanation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    transcript: Mapped[str] = mapped_column(Text, default="")
    gaps_flagged: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
