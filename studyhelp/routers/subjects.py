from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..classification import classify_and_file
from ..database import get_db
from ..models import Subject, Topic
from ..schemas import (
    ClassifiedItemCreate,
    ItemOut,
    SessionSummaryOut,
    SubjectCreate,
    SubjectMemoryOut,
    SubjectOut,
    TopicCreate,
    TopicOut,
)
from ..study import get_subject_memory, recent_summaries
from ..tutor import classify_item

router = APIRouter(prefix="/users/{user_id}/subjects", tags=["subjects"])


@router.post("", response_model=SubjectOut, status_code=201)
def create_subject(user_id: int, body: SubjectCreate, db: Session = Depends(get_db)):
    subject = Subject(user_id=user_id, **body.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("", response_model=list[SubjectOut])
def list_subjects(user_id: int, db: Session = Depends(get_db)):
    return list(db.scalars(select(Subject).where(Subject.user_id == user_id)))


@router.post("/{subject_id}/topics", response_model=TopicOut, status_code=201)
def create_topic(
    user_id: int, subject_id: int, body: TopicCreate, db: Session = Depends(get_db)
):
    subject = db.get(Subject, subject_id)
    if not subject or subject.user_id != user_id:
        raise HTTPException(404, "Subject not found")
    topic = Topic(subject_id=subject_id, **body.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.get("/{subject_id}/topics", response_model=list[TopicOut])
def list_topics(user_id: int, subject_id: int, db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Topic).where(Topic.subject_id == subject_id))
    )


@router.post("/{subject_id}/items", response_model=ItemOut, status_code=201)
def add_classified_item(
    user_id: int, subject_id: int, body: ClassifiedItemCreate,
    db: Session = Depends(get_db),
):
    """Add a hand-written item; classification files it into a topic
    automatically (creating the topic if needed), never rewriting the text."""
    subject = db.get(Subject, subject_id)
    if not subject or subject.user_id != user_id:
        raise HTTPException(404, "Subject not found")

    item = classify_and_file(
        db, subject_id, body.front, body.back, classify_item,
        item_type=body.type, worked_steps=body.worked_steps,
    )
    return ItemOut.from_item(item)


@router.get("/{subject_id}/memory", response_model=SubjectMemoryOut)
def subject_memory(user_id: int, subject_id: int, db: Session = Depends(get_db)):
    """The tutor's running notes on the student for this subject (read-only)."""
    subject = db.get(Subject, subject_id)
    if not subject or subject.user_id != user_id:
        raise HTTPException(404, "Subject not found")
    return SubjectMemoryOut(
        subject_id=subject_id,
        content=get_subject_memory(db, user_id, subject_id),
    )


@router.get("/{subject_id}/summaries", response_model=list[SessionSummaryOut])
def subject_summaries(user_id: int, subject_id: int, db: Session = Depends(get_db)):
    """Recent study-session summaries for this subject, newest first."""
    subject = db.get(Subject, subject_id)
    if not subject or subject.user_id != user_id:
        raise HTTPException(404, "Subject not found")
    return recent_summaries(db, user_id, subject_id, limit=10)
