"""LLM tutor engine using Claude API.

The tutor drives study sessions by asking questions, probing understanding,
and evaluating responses — following the study method from app.md.
"""

import json
import os
from datetime import datetime, timezone

from anthropic import Anthropic
from dotenv import load_dotenv

from .models import ItemType
from .study import MEMORY_CHAR_CAP  # single source of truth for the memory budget

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """\
You are a study tutor that forces active recall and deep understanding. You follow these rules strictly:

## Your role
- You ASK questions — you never lecture or explain unless the student got something wrong and needs correction.
- You are the "student" in the Feynman technique: the user explains concepts TO you, and you probe for gaps.
- You are Socratic: guide with questions, don't give answers.

## Session flow
You will receive context about what the student is studying (course, topic) and any due review items from their spaced-repetition schedule.

1. **Start** by asking a retrieval question. Either from a due review item, or about the topic they're studying.
2. **After the student answers:**
   - If CORRECT: acknowledge briefly, then probe deeper ("Why does that work?", "What would happen if...?", "Can you give an example?"). Then move to the next question.
   - If PARTIALLY correct: point out what's right, ask a targeted follow-up to fill the gap. Don't give the answer.
   - If WRONG: say it's not quite right (errors are learning, not failure). Give a small hint or rephrase the question. Let them try again.
   - If they say "I don't know" or are stuck: give a minimal hint. If still stuck, explain briefly, then immediately ask them to explain it back to you (Feynman technique).
3. **Vary question types:** mix concept questions, "when would you use this?", problem-solving, "explain this to a beginner", and "what's the difference between X and Y?"
4. **Interleave topics** when reviewing — don't ask 5 questions about the same concept in a row.

## Evaluation
After each student response, output a JSON block (hidden from the student) to rate their answer:
```json
{"rating": "AGAIN|HARD|GOOD|EASY", "was_correct": true|false, "item_summary": "brief description of what was tested", "item_ref": <id or null>}
```
Put this at the very end of your message, on its own line, wrapped in <eval>...</eval> tags. The student won't see this.

`item_ref` must be the `id` of the due review item you just tested (the number in its `(id:N)` tag). If your question was NOT about one of the listed due items — e.g. a general topic question or a follow-up probe not tied to a specific due item — set `item_ref` to null. Never invent an id that wasn't listed.

Rating guide:
- AGAIN: wrong, couldn't answer, or fundamental misunderstanding
- HARD: partially correct, needed hints, or took a long time to get there
- GOOD: correct with reasonable effort
- EASY: immediate, confident, perfect answer

## Style
- Be concise. Short questions, short feedback.
- Be encouraging but honest. "Not quite" is fine. Never say "Great job!" for a wrong answer.
- Use the student's course/topic context to make questions relevant.
- If the student asks YOU a question, answer it briefly, then immediately turn it into a retrieval question back at them.
- Don't use emojis.

## What you NEVER do
- Never let the student passively read. Every message from you should require them to think or respond.
- Never give long explanations unprompted. Only explain after a failed retrieval attempt.
- Never just say "correct" and move on — always probe at least once before moving to a new topic.
"""


# ── Study-session tutor (ADR-0004: teaches, writes no reviews) ────────────

# The phases of a phased study session, in order. The client owns the timer and
# tells the tutor which phase it is in; the tutor gauges level, teaches
# Socratically, probes a reflection, or winds down accordingly.
STUDY_PHASES = ("level_check", "work", "reflection", "wind_down")

_PHASE_GUIDANCE = {
    "level_check": (
        "PHASE: level check (untimed, before the focus timer starts). "
        "Gauge where the student is. If this is a new subject, ask a few "
        "questions to find their level. If continuing, recap from the subject "
        "memory below and confirm what they want to focus on today. Keep it "
        "short — you are orienting, not yet teaching."
    ),
    "work": (
        "PHASE: work interval (focus time). Teach Socratically: ask questions, "
        "probe understanding, hint after wrong answers. Never lecture unprompted."
    ),
    "reflection": (
        "PHASE: reflection (the closing minutes of a work interval). The "
        "student is recapping what they just learned so it consolidates before "
        "the break. Respond with probing questions that deepen the recap — "
        "never corrections, never new material. If this is the final interval, "
        "help them recap the whole session, not just the last topic."
    ),
    "wind_down": (
        "PHASE: wind-down (the session is ending). Help the student summarise "
        "what they covered and how it fits together. Ask what still feels shaky. "
        "Do not start new material."
    ),
}

STUDY_SYSTEM_PROMPT = """\
You are a study tutor for a focused, Pomodoro-structured study session. Your job \
is to help the student encode new material through active recall and explanation \
— never passive reading.

## Your role
- You ASK questions and probe understanding. You do not lecture unless the \
student got something wrong and needs a brief correction.
- You are Socratic: guide with questions, let the student do the thinking.
- You are the "student" in the Feynman technique: the user explains concepts TO \
you, and you probe for gaps.

## Phase
Each message tells you which phase of the session you are in (level check, work \
interval, reflection, or wind-down). Follow the guidance for the current phase. \
In particular, during a reflection you respond only with probing questions that \
help the student consolidate — you never correct and never introduce new \
material there.

## Subject memory and history
You may be given a private memory of this student for this subject (their level, \
gaps, misconceptions, topics covered) and short summaries of recent sessions. \
Use them to pick up where the last session left off, and to pitch questions at \
the right level. Never read this memory aloud verbatim.

## Style
- Be concise. Short questions, short feedback.
- Be encouraging but honest. "Not quite" is fine. Never say "Great job!" for a \
wrong answer.
- If the student asks YOU a question, answer briefly, then turn it back into a \
question for them.
- Don't use emojis.

## What you NEVER do
- Never let the student passively read. Every message should require them to \
think or respond.
- Never give long explanations unprompted. Only explain briefly after a failed \
attempt.
- Never grade the student or output any hidden rating — this is a teaching \
session, not a quiz.
"""


def build_study_context(
    subject_name: str,
    phase: str,
    subject_memory: str | None,
    recent_summaries: list[str] | None,
) -> str:
    """Assemble the study context prepended to the first user message.

    Carries the subject, the phase hint, the subject memory, and recent session
    summaries — and, by construction, no review items and no eval instructions.
    """
    if phase not in STUDY_PHASES:
        raise ValueError(f"Unknown study phase: {phase}")

    parts = [f"The student is studying: {subject_name}", _PHASE_GUIDANCE[phase]]

    if subject_memory:
        parts.append(f"What you remember about this student:\n{subject_memory}")

    if recent_summaries:
        recent = "\n".join(f"- {s}" for s in recent_summaries)
        parts.append(f"Recent sessions:\n{recent}")

    return "\n\n".join(parts)


def build_study_messages(
    phase: str,
    subject_name: str,
    messages: list[dict],
    subject_memory: str | None = None,
    recent_summaries: list[str] | None = None,
) -> list[dict]:
    """Build the API message list for a study-session turn.

    The study context is folded into the first user message (matching the
    existing tutor pattern). When there are no messages yet, we open the session
    with a phase-appropriate prompt.
    """
    context = build_study_context(subject_name, phase, subject_memory, recent_summaries)

    if not messages:
        return [{
            "role": "user",
            "content": f"[Study context]\n{context}\n\nI'm ready to start. Begin the session.",
        }]

    first = messages[0]
    if first["role"] != "user":
        # Conversation opened with an assistant turn (our opener); fold context
        # into the first user reply instead.
        api_messages = [first]
        for i, msg in enumerate(messages[1:], start=1):
            if msg["role"] == "user":
                api_messages.append({
                    "role": "user",
                    "content": f"[Study context]\n{context}\n\n[Student says]\n{msg['content']}",
                })
                api_messages.extend(messages[i + 1:])
                return api_messages
            api_messages.append(msg)
        return api_messages

    api_messages = [{
        "role": "user",
        "content": f"[Study context]\n{context}\n\n[Student says]\n{first['content']}",
    }]
    api_messages.extend(messages[1:])
    return api_messages


def study_chat(
    phase: str,
    subject_name: str,
    messages: list[dict],
    subject_memory: str | None = None,
    recent_summaries: list[str] | None = None,
) -> str:
    """Send a study-session turn to the tutor and return its reply text.

    Thin, untested wrapper around the Claude API; all prompt assembly lives in
    the pure builders above.
    """
    api_messages = build_study_messages(
        phase, subject_name, messages, subject_memory, recent_summaries
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=STUDY_SYSTEM_PROMPT,
        messages=api_messages,
    )
    return response.content[0].text


def build_context(course_name: str, topic_name: str | None, due_items: list[dict]) -> str:
    """Build the context message that tells the tutor what to focus on."""
    ctx = f"The student is studying: {course_name}"
    if topic_name:
        ctx += f" > {topic_name}"
    ctx += "\n"

    if due_items:
        ctx += "\nDue review items (ask about these, interleaved). Each is tagged "
        ctx += "with a stable id — cite it as item_ref in your eval when you test that item:\n"
        for item in due_items[:10]:  # Cap at 10 to avoid context bloat
            ctx += f"- (id:{item['id']}) [{item['type']}] {item['front']}"
            if item.get('back'):
                ctx += f" (answer: {item['back']})"
            ctx += "\n"
    else:
        ctx += "\nNo specific review items due. Ask questions about the topic based on what the student tells you they're working on.\n"

    return ctx


def chat(messages: list[dict], course_name: str, topic_name: str | None,
         due_items: list[dict]) -> str:
    """Send a chat message to the tutor and get a response.

    messages: list of {"role": "user"|"assistant", "content": "..."}
    Returns the assistant's response text.
    """
    context = build_context(course_name, topic_name, due_items)

    # Prepend context as the first user message if this is the start
    api_messages = []
    if messages:
        # Add context to the first user message
        first = messages[0]
        if first["role"] == "user":
            api_messages.append({
                "role": "user",
                "content": f"[Study context]\n{context}\n\n[Student says]\n{first['content']}"
            })
            api_messages.extend(messages[1:])
        else:
            api_messages = list(messages)
    else:
        # No messages yet — start the session
        api_messages = [{
            "role": "user",
            "content": f"[Study context]\n{context}\n\nI'm ready to start studying. Quiz me."
        }]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=api_messages,
    )

    return response.content[0].text


def resolve_reviewed_item(eval_data: dict | None, due_items: list[dict]) -> int | None:
    """Decide which due item the tutor's evaluation should be logged against.

    The tutor names the item it tested via `item_ref` in its eval block (the id
    we surfaced in its study context). We return that id only when it matches an
    item that was genuinely in `due_items` — so a missing, malformed, or
    hallucinated ref resolves to None and no review is written. This is what
    keeps a chat review's prediction and outcome referring to the same item.
    """
    if not eval_data or not due_items:
        return None

    ref = eval_data.get("item_ref")
    # Reject None and bool up front: bool is an int subclass, so `int(True)` would
    # otherwise silently resolve to id 1 — a wrong-type ref must not attribute.
    if ref is None or isinstance(ref, bool):
        return None

    try:
        ref_id = int(ref)
    except (ValueError, TypeError):
        return None

    due_ids = {item["id"] for item in due_items}
    return ref_id if ref_id in due_ids else None


def parse_eval(response_text: str) -> tuple[str, dict | None]:
    """Extract the <eval> block from a tutor response.

    Returns (clean_text, eval_dict) where clean_text has the eval block removed.
    """
    import re
    match = re.search(r'<eval>\s*(\{.*?\})\s*</eval>', response_text, re.DOTALL)
    if match:
        clean = response_text[:match.start()].rstrip()
        try:
            eval_data = json.loads(match.group(1))
            return clean, eval_data
        except json.JSONDecodeError:
            return clean, None
    return response_text, None


# ── Session summary + subject-memory rewrite (ADR-0004, stories 13-17) ────

def build_summary_prompt(transcript: str, notes: str, recap: str,
                         prior_memory: str = "") -> str:
    """Prompt for the single end-of-session call that writes the session summary
    and rewrites the subject memory."""
    return (
        "A study session just ended. Produce two things as JSON.\n\n"
        f"Transcript:\n{transcript or '(none)'}\n\n"
        f"Student's notes:\n{notes or '(none)'}\n\n"
        f"Student's own wind-down recap:\n{recap or '(none)'}\n\n"
        f"Your prior memory of this student:\n{prior_memory or '(none)'}\n\n"
        "Return exactly one JSON object with two string keys:\n"
        '  "summary": a short recap of what this session covered.\n'
        '  "memory": your REWRITTEN running notes on this student for this '
        "subject — their level, gaps, misconceptions, and topics covered. "
        "Rewrite it wholesale from the prior memory plus this session; do not "
        f"simply append. Keep it under {MEMORY_CHAR_CAP} characters.\n"
    )


def parse_summary(text: str) -> dict:
    """Extract {"summary", "memory"} from the model's output. Malformed output
    falls back to the whole text as the summary and an empty memory, so a bad
    call never corrupts the stored subject memory."""
    data = _extract_json(text)
    if isinstance(data, dict):
        return {"summary": _as_str(data.get("summary")),
                "memory": _as_str(data.get("memory"))}
    return {"summary": text.strip(), "memory": ""}


def generate_summary_and_memory(
    transcript: str, notes: str, recap: str, prior_memory: str = ""
) -> dict:
    prompt = build_summary_prompt(transcript, notes, recap, prior_memory)
    response = client.messages.create(
        model=MODEL, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_summary(response.content[0].text)


# ── Card drafts (ADR-0004, stories 18-19) ────────────────────────────────

def build_drafts_prompt(notes: str, summary: str) -> str:
    types = ", ".join(t.value for t in ItemType)
    return (
        "From this study session's notes and summary, propose review cards the "
        "student can add to their deck. Use their material; do not invent facts "
        "they did not study.\n\n"
        f"Notes:\n{notes or '(none)'}\n\n"
        f"Summary:\n{summary or '(none)'}\n\n"
        'Return one JSON object: {"drafts": [{"front": ..., "back": ..., '
        '"type": ...}]}. front is the prompt, back is the answer, and type is '
        f"one of: {types}. Propose at most 8 cards.\n"
    )


def parse_drafts(text: str) -> list[dict]:
    """Extract proposed cards. Entries without a front are dropped; unknown types
    default to CONCEPT_QA. Malformed output yields an empty list."""
    data = _extract_json(text)
    if not isinstance(data, dict):
        return []
    raw = data.get("drafts")
    if not isinstance(raw, list):
        return []
    drafts = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        front = _as_str(entry.get("front")).strip()
        if not front:
            continue
        drafts.append({
            "front": front,
            "back": _as_str(entry.get("back")).strip(),
            "type": _coerce_type(entry.get("type")),
        })
    return drafts


def generate_drafts(notes: str, summary: str) -> list[dict]:
    prompt = build_drafts_prompt(notes, summary)
    response = client.messages.create(
        model=MODEL, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_drafts(response.content[0].text)


# ── Classification (ADR-0004, stories 20-21) ─────────────────────────────

def build_classification_prompt(
    front: str, back: str, existing_topics: list[str]
) -> str:
    types = ", ".join(t.value for t in ItemType)
    topics = ", ".join(existing_topics) if existing_topics else "(none yet)"
    return (
        "File this study item into a topic. Do NOT rewrite the item's text.\n\n"
        f"Item prompt: {front}\n"
        f"Item answer: {back or '(none)'}\n\n"
        f"Existing topics in this subject: {topics}\n\n"
        "Pick an existing topic if one fits; otherwise name a new, concise "
        'topic. Return one JSON object: {"topic": "...", "type": "..."} where '
        f"type is one of: {types}.\n"
    )


def parse_classification(text: str) -> dict:
    """Extract {"topic", "type"}. Topic is "" and type None when unparseable,
    letting the caller fall back to a default topic."""
    data = _extract_json(text)
    if not isinstance(data, dict):
        return {"topic": "", "type": None}
    return {
        "topic": _as_str(data.get("topic")).strip(),
        "type": _coerce_type(data.get("type")) if data.get("type") is not None else None,
    }


def classify_item(front: str, back: str, existing_topics: list[str]) -> dict:
    prompt = build_classification_prompt(front, back, existing_topics)
    response = client.messages.create(
        model=MODEL, max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_classification(response.content[0].text)


# ── shared parsing helpers ───────────────────────────────────────────────

def _extract_json(text: str):
    """Best-effort: parse the first balanced JSON object in the text, tolerating
    surrounding prose and ```json fences. Returns None if none parses."""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        start = None
    return None


def _as_str(value) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def _coerce_type(value) -> ItemType:
    """Map a model-supplied type name onto ItemType, defaulting to CONCEPT_QA."""
    if isinstance(value, str):
        try:
            return ItemType(value.strip().upper())
        except ValueError:
            pass
    return ItemType.CONCEPT_QA
