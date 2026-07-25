"""Tests for review-session commentary (issue #6, ADR-0004).

Commentary is the LLM's feedback on a typed answer. Its contract has NO rating
field at all: the user's self-assessment alone drives FSRS, so commentary can
never set or override a rating. These pure builder/parser functions are the LLM
boundary — tested without any API call.
"""

from studyhelp.commentary import build_commentary_prompt, parse_commentary


def test_prompt_includes_the_three_inputs():
    system, messages = build_commentary_prompt(
        item_prompt="What is the derivative of x^2?",
        canonical_answer="2x",
        typed_answer="i think it's 2x",
    )
    joined = system + " " + " ".join(m["content"] for m in messages)
    assert "What is the derivative of x^2?" in joined
    assert "2x" in joined
    assert "i think it's 2x" in joined


def test_prompt_never_asks_for_a_rating():
    """The contract must not mention rating/grade/score — nothing the model
    could fill in to influence scheduling."""
    system, messages = build_commentary_prompt("q", "a", "attempt")
    text = (system + " " + " ".join(m["content"] for m in messages)).lower()
    for forbidden in ("rating", "grade", "score", "again", "hard", "good", "easy",
                      "<eval>", "json"):
        assert forbidden not in text


def test_parse_returns_plain_feedback_untouched():
    raw = "Good attempt. You have the right idea but missed the chain rule."
    assert parse_commentary(raw) == raw.strip()


def test_parse_strips_a_smuggled_eval_block():
    # Even if the model tries to emit a rating block, it must never survive into
    # what we store or show — commentary cannot carry a rating.
    raw = ('Nicely done, that is correct.\n'
           '<eval>{"rating": "EASY", "was_correct": true}</eval>')
    cleaned = parse_commentary(raw)
    assert "eval" not in cleaned.lower()
    assert "EASY" not in cleaned
    assert cleaned == "Nicely done, that is correct."


def test_parse_strips_a_smuggled_json_rating_block():
    raw = ('You missed a case.\n'
           '```json\n{"rating": "AGAIN"}\n```')
    cleaned = parse_commentary(raw)
    assert "AGAIN" not in cleaned
    assert "rating" not in cleaned.lower()
    assert cleaned == "You missed a case."


def test_parse_strips_a_bare_rating_object():
    raw = 'Correct. {"rating": "GOOD"}'
    cleaned = parse_commentary(raw)
    assert "GOOD" not in cleaned
    assert cleaned == "Correct."


def test_parse_keeps_ordinary_braces_in_feedback():
    # A set literal in feedback on a CS card must survive — only rating-bearing
    # objects are stripped, not every brace.
    raw = 'Right, the set is {a, b}. Watch the ordering though.'
    assert parse_commentary(raw) == raw.strip()


def test_parse_handles_empty_and_whitespace():
    assert parse_commentary("") == ""
    assert parse_commentary("   \n  ") == ""
