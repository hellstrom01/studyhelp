"""Tests for the classification / topic-resolution service.

Classification files a user-authored Item into a topic (creating it if needed)
and may suggest a type — but it never rewrites the user's words (CONTEXT.md).
The LLM's parsed classification is fed past the API boundary as a dict, so these
tests never call the model. Topic resolution is idempotent by name within a
subject.
"""

from sqlalchemy import select

from studyhelp.classification import DEFAULT_TOPIC, file_item, resolve_topic
from studyhelp.models import ItemType, Topic


def test_files_item_into_a_new_topic(db, seed):
    subj = seed.subject()
    item = file_item(
        db, subj.id, front="What is a limit?", back="A value a function approaches.",
        classification={"topic": "Limits", "type": ItemType.CONCEPT_QA},
    )
    assert item.topic.name == "Limits"
    assert item.topic.subject_id == subj.id


def test_reuses_existing_topic_by_name(db, seed):
    subj = seed.subject()
    first = file_item(db, subj.id, front="Q1", back="A1",
                      classification={"topic": "Derivatives", "type": None})
    second = file_item(db, subj.id, front="Q2", back="A2",
                       classification={"topic": "Derivatives", "type": None})

    assert first.topic_id == second.topic_id
    topics = list(db.scalars(
        select(Topic).where(Topic.subject_id == subj.id, Topic.name == "Derivatives")
    ))
    assert len(topics) == 1


def test_never_rewrites_the_users_text(db, seed):
    subj = seed.subject()
    item = file_item(
        db, subj.id, front="  the users EXACT words  ", back="verbatim answer",
        classification={"topic": "T", "type": ItemType.CONCEPT_QA},
    )
    assert item.front == "  the users EXACT words  "
    assert item.back == "verbatim answer"


def test_user_supplied_type_wins_over_suggestion(db, seed):
    subj = seed.subject()
    item = file_item(
        db, subj.id, front="Prove X", back="proof",
        classification={"topic": "Proofs", "type": ItemType.CONCEPT_QA},
        item_type=ItemType.PROBLEM_HIDDEN,
    )
    assert item.type == ItemType.PROBLEM_HIDDEN


def test_suggested_type_used_when_user_gave_none(db, seed):
    subj = seed.subject()
    item = file_item(
        db, subj.id, front="def f():", back="code",
        classification={"topic": "Functions", "type": ItemType.CODE_FROM_SCRATCH},
    )
    assert item.type == ItemType.CODE_FROM_SCRATCH


def test_empty_topic_falls_back_to_default(db, seed):
    subj = seed.subject()
    item = file_item(
        db, subj.id, front="Q", back="A",
        classification={"topic": "", "type": None},
    )
    assert item.topic.name == DEFAULT_TOPIC


def test_resolve_topic_is_idempotent(db, seed):
    subj = seed.subject()
    t1 = resolve_topic(db, subj.id, "Series")
    t2 = resolve_topic(db, subj.id, "Series")
    assert t1.id == t2.id


def test_same_topic_name_in_different_subjects_are_distinct(db, seed):
    a = seed.subject("A")
    b = seed.subject("B")
    ta = resolve_topic(db, a.id, "Shared")
    tb = resolve_topic(db, b.id, "Shared")
    assert ta.id != tb.id
