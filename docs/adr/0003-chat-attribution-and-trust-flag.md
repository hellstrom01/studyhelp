# ADR-0003: Exact chat attribution and a per-review trust flag

Status: Accepted (2026-07-24)

Amends ADR-0001.

## Context

ADR-0001 excluded all tutor-chat reviews from calibration because the chat path
attributed every outcome to `due_items[0]` rather than the item actually quizzed,
so a stored `predicted_recall` (item A) could be paired with an outcome belonging
to item B. It anticipated this fix: "when the tutor path is fixed to attribute
outcomes to the real item, CHAT reviews can be promoted to trustworthy (or a
finer-grained trust flag added)."

Because the tutor chat is the primary study flow, the calibration dashboard sat
permanently in its "not enough data yet" state — the only reviews being written
were the untrustworthy kind.

## Decision

**Attribute chat outcomes to the item actually quizzed.** The tutor's study
context now tags each due item with its id, and the tutor names the tested item
via an `item_ref` field in its `<eval>` block. A pure resolver
(`tutor.resolve_reviewed_item`) maps that ref back to a due item, guarding against
missing, malformed, or hallucinated refs by resolving to `None` — in which case
no review is logged (an improvement over the previous always-attribute-to-first
guess). The chat path logs the review against the resolved item, so its
prediction and outcome refer to the same item by construction.

**Move the trust signal onto the review.** Add a nullable
`Review.attribution_exact`. It is `true` when a review's prediction and outcome
provably refer to the same item: always for CARD reviews, and for CHAT reviews
that were resolved to a specific item. `submit_review` sets it on every review it
writes. Calibration's trustworthy filter changes from `source == CARD` to
`attribution_exact is True` (still requiring a non-null `predicted_recall`).

`source` still records provenance (CARD vs CHAT) and feeds the coverage counts;
the excluded-chat count now reports chat reviews that did *not* count (legacy /
unattributed), so the coverage note stays honest.

## Consequences

- The dashboard fills up from ordinary tutor sessions, leaving its empty state
  after ~20 exactly-attributed reviews accumulate.
- Legacy chat rows written before this change have `attribution_exact` null/false
  and remain excluded; no migration or backfill is performed.
- Trust is now legible per review rather than inferred from source alone, so
  future flows can opt in by setting the flag.
- ADR-0002 (compute fresh, never read `StudySession.avg_calibration_error`) is
  unaffected and still holds.
