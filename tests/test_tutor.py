"""Tests for the tutor's attribution decision.

`resolve_reviewed_item` is a pure function: given the tutor's parsed eval block
and the list of due items that were in its context, it decides which item the
outcome should be logged against — or None when it cannot be sure. This is the
seam that fixes the mis-attribution bug (issue #3), so it is tested exhaustively
without the LLM or the database.
"""

from studyhelp.tutor import resolve_reviewed_item


def _due(*ids):
    """Build a minimal due-items list (only `id` matters to the resolver)."""
    return [{"id": i, "type": "CONCEPT_QA", "front": "q", "back": "a", "topic": "T"}
            for i in ids]


def test_matching_ref_returns_that_item_id():
    due = _due(10, 20, 30)
    assert resolve_reviewed_item({"item_ref": 20}, due) == 20


def test_ref_can_be_a_numeric_string():
    # The model may emit the id as a JSON string; coerce and match.
    due = _due(10, 20, 30)
    assert resolve_reviewed_item({"item_ref": "20"}, due) == 20


def test_missing_ref_returns_none():
    due = _due(10, 20)
    assert resolve_reviewed_item({"rating": "GOOD"}, due) is None


def test_null_ref_returns_none():
    due = _due(10, 20)
    assert resolve_reviewed_item({"item_ref": None}, due) is None


def test_malformed_ref_returns_none():
    due = _due(10, 20)
    assert resolve_reviewed_item({"item_ref": "not-a-number"}, due) is None


def test_bool_ref_returns_none():
    # bool is an int subclass; `int(True)` would be 1. A wrong-type ref must not
    # silently attribute to the item with id 1.
    due = _due(1, 2, 3)
    assert resolve_reviewed_item({"item_ref": True}, due) is None
    assert resolve_reviewed_item({"item_ref": False}, due) is None


def test_hallucinated_ref_not_in_due_set_returns_none():
    # The model names an id that was never in its context — never write a review
    # against an item it did not actually have.
    due = _due(10, 20, 30)
    assert resolve_reviewed_item({"item_ref": 999}, due) is None


def test_none_eval_returns_none():
    assert resolve_reviewed_item(None, _due(10)) is None


def test_empty_due_items_returns_none():
    assert resolve_reviewed_item({"item_ref": 10}, []) is None


def test_returned_id_is_always_from_the_due_set():
    due = _due(10, 20, 30)
    for ref in (10, 20, 30):
        assert resolve_reviewed_item({"item_ref": ref}, due) in {10, 20, 30}
