from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Item, Topic
from ..schemas import ItemCreate, ItemOut

router = APIRouter(prefix="/topics/{topic_id}/items", tags=["items"])


@router.post("", response_model=ItemOut, status_code=201)
def create_item(topic_id: int, body: ItemCreate, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    item = Item(topic_id=topic_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return ItemOut.from_item(item)


@router.get("", response_model=list[ItemOut])
def list_items(topic_id: int, db: Session = Depends(get_db)):
    items = list(db.scalars(select(Item).where(Item.topic_id == topic_id)))
    return [ItemOut.from_item(i) for i in items]


@router.get("/{item_id}", response_model=ItemOut)
def get_item(topic_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item or item.topic_id != topic_id:
        raise HTTPException(404, "Item not found")
    return ItemOut.from_item(item)
