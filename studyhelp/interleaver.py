"""Interleaving engine (Section 5.5).

Reorders a list of items so that no two consecutive items share the same
topic or type, maximizing discrimination practice.
"""

import random

from .models import Item


def interleave(items: list[Item]) -> list[Item]:
    """Reorder items to maximize topic and type alternation.

    Uses a greedy algorithm: from the remaining pool, pick an item whose
    topic AND type both differ from the previous item. Falls back to
    topic-only difference, then type-only, then any remaining item.
    """
    if len(items) <= 1:
        return list(items)

    pool = list(items)
    random.shuffle(pool)
    result: list[Item] = [pool.pop()]

    while pool:
        prev = result[-1]
        best_idx = _pick_best(pool, prev)
        result.append(pool.pop(best_idx))

    return result


def _pick_best(pool: list[Item], prev: Item) -> int:
    """Find the best next item index from the pool."""
    # Priority: differ on both > differ on topic > differ on type > any
    diff_both = []
    diff_topic = []
    diff_type = []

    for i, item in enumerate(pool):
        topic_diff = item.topic_id != prev.topic_id
        type_diff = item.type != prev.type
        if topic_diff and type_diff:
            diff_both.append(i)
        elif topic_diff:
            diff_topic.append(i)
        elif type_diff:
            diff_type.append(i)

    candidates = diff_both or diff_topic or diff_type
    if candidates:
        return random.choice(candidates)
    return 0


def interleave_mixed_practice(items: list[Item], n: int) -> list[Item]:
    """Generate an interleaved problem set of N items spanning many topics.

    Used for exam-simulation / mixed practice mode (Section 5.5 bullet 3).
    Selects items to maximize topic diversity, then interleaves.
    """
    if n >= len(items):
        return interleave(items)

    # Group by topic, round-robin pick to maximize topic spread
    by_topic: dict[int, list[Item]] = {}
    for item in items:
        by_topic.setdefault(item.topic_id, []).append(item)

    for v in by_topic.values():
        random.shuffle(v)

    selected: list[Item] = []
    topic_ids = list(by_topic.keys())
    random.shuffle(topic_ids)

    idx = 0
    while len(selected) < n:
        tid = topic_ids[idx % len(topic_ids)]
        if by_topic[tid]:
            selected.append(by_topic[tid].pop())
        idx += 1
        # If we've gone around and all are empty, break
        if idx - len(selected) > len(topic_ids):
            break

    return interleave(selected)
