"""Review-session commentary (issue #6, ADR-0004).

In a review session the user types an answer, the LLM comments on the attempt,
and then the *user* rates themselves. The commentary contract deliberately has
no rating field at all: the LLM's feedback never sets or overrides the FSRS
grade. The prompt builder and output parser are pure functions (the LLM
boundary); the API call itself is a thin, untested wrapper.
"""

import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """\
You give brief feedback on a student's attempt to recall a flashcard answer.

You will be shown the card's prompt, its correct answer, and the student's typed
attempt. Comment on the attempt: say what they got right, and point out anything
missing or wrong, in two or three sentences at most.

Rules:
- Be concise and specific. No preamble, no restating the question.
- Do not tell the student how well they did on any scale, and do not judge their
  recall for them — they assess themselves after reading your feedback.
- Output only the feedback prose. No tags, code blocks, or structured metadata.
- Do not use emojis.
"""

# Anything that looks like a smuggled control block — an <eval>…</eval> tag, a
# fenced code block, or a loose object carrying a rating-like key — is stripped
# defensively so a stray rating can never reach what we store or show. The loose
# matcher requires a rating/grade/score key so ordinary braces in feedback (a
# set literal on a CS card, say) survive untouched.
_EVAL_TAG = re.compile(r"<eval>.*?</eval>", re.DOTALL | re.IGNORECASE)
_JSON_FENCE = re.compile(r"```.*?```", re.DOTALL)
_RATING_OBJECT = re.compile(
    r"\{[^{}]*\"(?:rating|grade|score|was_correct)\"[^{}]*\}",
    re.DOTALL | re.IGNORECASE,
)


def build_commentary_prompt(
    item_prompt: str, canonical_answer: str, typed_answer: str
) -> tuple[str, list[dict]]:
    """Assemble the (system, messages) for a commentary call. Pure."""
    user = (
        f"Card prompt:\n{item_prompt}\n\n"
        f"Correct answer:\n{canonical_answer}\n\n"
        f"Student's attempt:\n{typed_answer}"
    )
    return SYSTEM_PROMPT, [{"role": "user", "content": user}]


def parse_commentary(raw: str) -> str:
    """Return clean feedback prose, stripping any smuggled control block. Pure."""
    text = _EVAL_TAG.sub("", raw)
    text = _JSON_FENCE.sub("", text)
    text = _RATING_OBJECT.sub("", text)
    return text.strip()


def comment_on_attempt(
    item_prompt: str, canonical_answer: str, typed_answer: str
) -> str:
    """Thin API wrapper: build the prompt, call Claude, parse the reply."""
    system, messages = build_commentary_prompt(
        item_prompt, canonical_answer, typed_answer
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=system,
        messages=messages,
    )
    return parse_commentary(response.content[0].text)
