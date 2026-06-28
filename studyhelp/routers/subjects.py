from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Subject, Topic
from ..schemas import SubjectCreate, SubjectOut, TopicCreate, TopicOut

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
