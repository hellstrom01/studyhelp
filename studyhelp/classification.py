"""Classification & topic resolution (ADR-0004, CONTEXT.md).

Every Item entering the deck — an accepted card draft or a hand-written one — is
filed into a topic here. The LLM's parsed classification supplies a topic name
(existing or new) and a suggested type; this service resolves the topic
idempotently within the subject and creates the Item. It never touches the
user's prompt/answer text: classification files, it does not author.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Item, ItemType, Topic

# Where items land when classification can't name a topic — the taxonomy is
# never the user's job, so we always have somewhere to file.
DEFAULT_TOPIC = "General"


def resolve_topic(db: Session, subject_id: int, name: str) -> Topic:
    """Return the subject's topic with this name, creating it if absent.
    Idempotent by (subject, name): repeated calls reuse the same row."""
    name = (name or "").strip() or DEFAULT_TOPIC
    topic = db.scalar(
        select(Topic).where(Topic.subject_id == subject_id, Topic.name == name)
    )
    if topic is None:
        topic = Topic(subject_id=subject_id, name=name)
        db.add(topic)
        db.flush()
    return topic


def classify_and_file(
    db: Session,
    subject_id: int,
    front: str,
    back: str,
    classifier,
    item_type: ItemType | None = None,
    worked_steps: list[str] | None = None,
) -> Item:
    """Classify a user-authored item against the subject's existing topics, then
    file it. `classifier(front, back, existing_topic_names)` is the LLM call,
    injected so this module stays LLM-free and testable; a failed call falls back
    to the default topic rather than blocking the add.
    """
    existing = list(db.scalars(select(Topic.name).where(Topic.subject_id == subject_id)))
    try:
        classification = classifier(front, back, existing)
    except Exception:
        classification = {"topic": "", "type": None}
    return file_item(
        db, subject_id, front=front, back=back,
        classification=classification, item_type=item_type,
        worked_steps=worked_steps,
    )


def file_item(
    db: Session,
    subject_id: int,
    front: str,
    back: str,
    classification: dict,
    item_type: ItemType | None = None,
    worked_steps: list[str] | None = None,
) -> Item:
    """Create an Item in the subject, filed into the classified topic.

    `classification` is the parsed LLM output {"topic", "type"}. The user's
    `item_type` wins when given; otherwise the suggested type is used, falling
    back to CONCEPT_QA. `front`/`back` are stored verbatim — never rewritten.
    """
    topic = resolve_topic(db, subject_id, classification.get("topic", ""))

    chosen_type = item_type or classification.get("type") or ItemType.CONCEPT_QA

    item = Item(
        topic_id=topic.id,
        type=chosen_type,
        front=front,
        back=back,
        worked_steps=worked_steps,
    )
    db.add(item)
    db.commit()
    return item
