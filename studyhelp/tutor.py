"""LLM tutor engine using Claude API.

The tutor drives study sessions by asking questions, probing understanding,
and evaluating responses — following the study method from app.md.
"""

import json
import os
from datetime import datetime, timezone

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
{"rating": "AGAIN|HARD|GOOD|EASY", "was_correct": true|false, "item_summary": "brief description of what was tested"}
```
Put this at the very end of your message, on its own line, wrapped in <eval>...</eval> tags. The student won't see this.

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


def build_context(course_name: str, topic_name: str | None, due_items: list[dict]) -> str:
    """Build the context message that tells the tutor what to focus on."""
    ctx = f"The student is studying: {course_name}"
    if topic_name:
        ctx += f" > {topic_name}"
    ctx += "\n"

    if due_items:
        ctx += "\nDue review items (ask about these, interleaved):\n"
        for item in due_items[:10]:  # Cap at 10 to avoid context bloat
            ctx += f"- [{item['type']}] {item['front']}"
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
