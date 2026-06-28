"""Pydantic schemas for the API layer."""

from datetime import datetime

from pydantic import BaseModel

from .models import FSRSState, ItemType, Rating, SubjectType


# ── User ─────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    display_name: str
    target_retention: float = 0.90
    daily_new_limit: int = 20
    daily_review_limit: int = 100
    pomodoro_focus_min: int = 25
    break_min: int = 5
    sleep_reminder_time: str | None = None


class UserOut(UserCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Subject ──────────────────────────────────────────────────────────────

class SubjectCreate(BaseModel):
    name: str
    type: SubjectType
    color: str = "#4A90D9"


class SubjectOut(SubjectCreate):
    id: int
    user_id: int
    model_config = {"from_attributes": True}


# ── Topic ────────────────────────────────────────────────────────────────

class TopicCreate(BaseModel):
    name: str
    parent_topic_id: int | None = None


class TopicOut(TopicCreate):
    id: int
    subject_id: int
    model_config = {"from_attributes": True}


# ── Item ─────────────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    type: ItemType
    front: str
    back: str = ""
    worked_steps: list[str] | None = None
    diagram_url: str | None = None
    difficulty_tag: str | None = None
    source_ref: str | None = None


class FSRSOut(BaseModel):
    stability: float | None = None
    difficulty: float | None = None
    due: datetime | None = None
    last_review: datetime | None = None
    step: int = 0
    state: FSRSState = FSRSState.NEW

    model_config = {"from_attributes": True}


class ItemOut(BaseModel):
    id: int
    topic_id: int
    type: ItemType
    front: str
    back: str
    worked_steps: list[str] | None = None
    diagram_url: str | None = None
    difficulty_tag: str | None = None
    source_ref: str | None = None
    created_at: datetime
    fsrs: FSRSOut

    model_config = {"from_attributes": True}

    @classmethod
    def from_item(cls, item) -> "ItemOut":
        return cls(
            id=item.id,
            topic_id=item.topic_id,
            type=item.type,
            front=item.front,
            back=item.back,
            worked_steps=item.worked_steps,
            diagram_url=item.diagram_url,
            difficulty_tag=item.difficulty_tag,
            source_ref=item.source_ref,
            created_at=item.created_at,
            fsrs=FSRSOut(
                stability=item.fsrs_stability,
                difficulty=item.fsrs_difficulty,
                due=item.fsrs_due,
                last_review=item.fsrs_last_review,
                step=item.fsrs_step,
                state=item.fsrs_state,
            ),
        )


# ── Review ───────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    rating: Rating
    was_correct: bool
    response_ms: int | None = None


class ReviewOut(BaseModel):
    id: int
    item_id: int
    rating_given: Rating
    predicted_recall: float | None
    was_correct: bool
    response_ms: int | None
    reviewed_at: datetime

    model_config = {"from_attributes": True}


# ── Session ──────────────────────────────────────────────────────────────

class SessionOut(BaseModel):
    id: int
    user_id: int
    started_at: datetime
    ended_at: datetime | None
    items_seen: int
    new_count: int
    review_count: int
    pomodoros_completed: int
    avg_calibration_error: float | None

    model_config = {"from_attributes": True}


# ── Queue item (what the session player serves) ──────────────────────────

class QueueItem(BaseModel):
    item_id: int
    topic_id: int
    topic_name: str
    subject_name: str
    type: ItemType
    front: str
    worked_steps: list[str] | None = None
    diagram_url: str | None = None
    is_new: bool
    predicted_recall: float | None
    steps_to_reveal: int | None = None  # for faded worked examples


class SessionQueue(BaseModel):
    session_id: int
    items: list[QueueItem]
    total_reviews: int
    total_new: int
