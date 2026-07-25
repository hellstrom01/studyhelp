"""Tests for the tutor's structured-output parsers (issue #5, ADR-0004).

Session summary, card drafts, and classification each go through a pure parser
that must survive well-formed, prose-wrapped, malformed, and hostile model
output. Tested without any API call.
"""

from studyhelp.models import ItemType
from studyhelp.tutor import parse_classification, parse_drafts, parse_summary


# ── parse_summary ────────────────────────────────────────────────────────

def test_parse_summary_extracts_summary_and_memory():
    out = parse_summary('{"summary": "Did eigenvalues.", "memory": "Knows scaling."}')
    assert out["summary"] == "Did eigenvalues."
    assert out["memory"] == "Knows scaling."


def test_parse_summary_tolerates_prose_and_fences():
    raw = 'Here you go:\n```json\n{"summary": "s", "memory": "m"}\n```\nHope that helps!'
    out = parse_summary(raw)
    assert out["summary"] == "s"
    assert out["memory"] == "m"


def test_parse_summary_malformed_falls_back_to_text_summary_empty_memory():
    out = parse_summary("not json at all")
    assert isinstance(out["summary"], str)
    assert out["memory"] == ""


# ── parse_drafts ─────────────────────────────────────────────────────────

def test_parse_drafts_returns_typed_items():
    raw = ('{"drafts": [{"front": "What is an eigenvalue?", "back": "A scalar.",'
           ' "type": "CONCEPT_QA"}]}')
    drafts = parse_drafts(raw)
    assert len(drafts) == 1
    assert drafts[0]["front"] == "What is an eigenvalue?"
    assert drafts[0]["back"] == "A scalar."
    assert drafts[0]["type"] == ItemType.CONCEPT_QA


def test_parse_drafts_defaults_unknown_type_to_concept_qa():
    raw = '{"drafts": [{"front": "Q", "back": "A", "type": "NONSENSE"}]}'
    assert parse_drafts(raw)[0]["type"] == ItemType.CONCEPT_QA


def test_parse_drafts_skips_entries_without_a_front():
    raw = '{"drafts": [{"back": "orphan answer"}, {"front": "Q", "back": "A"}]}'
    assert [d["front"] for d in parse_drafts(raw)] == ["Q"]


def test_parse_drafts_malformed_returns_empty_list():
    assert parse_drafts("the model refused") == []
    assert parse_drafts('{"drafts": "not a list"}') == []


# ── parse_classification ─────────────────────────────────────────────────

def test_parse_classification_extracts_topic_and_type():
    out = parse_classification('{"topic": "Eigenvalues", "type": "CONCEPT_QA"}')
    assert out["topic"] == "Eigenvalues"
    assert out["type"] == ItemType.CONCEPT_QA


def test_parse_classification_type_optional():
    out = parse_classification('{"topic": "Limits"}')
    assert out["topic"] == "Limits"
    assert out["type"] is None


def test_parse_classification_malformed_returns_empty_topic():
    out = parse_classification("nope")
    assert out["topic"] == ""
    assert out["type"] is None
