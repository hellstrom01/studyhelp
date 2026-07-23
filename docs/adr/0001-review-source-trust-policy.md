# ADR-0001: Review source discriminator and calibration trust policy

Status: Accepted (2026-07-23)

## Context

The calibration dashboard measures the gap between predicted recall (stored per
review as `predicted_recall`) and actual outcome (`was_correct`). This is only
meaningful when both refer to the *same* item.

Two flows write reviews:

- **Card player** (`routers/sessions.py` → `submit_review`): the prediction and
  the outcome are for the same item. Trustworthy.
- **Tutor chat** (`routers/chat.py` → `_try_log_review`): the tutor's rating is
  attributed to `due_items[0]`, which is often *not* the item actually quizzed.
  The stored `predicted_recall` (item A) is therefore paired with an outcome that
  may belong to item B. Not trustworthy for calibration.

Since the tutor chat is now the primary study flow, most review traffic is the
untrustworthy kind, and reviews carried no marker distinguishing the two.

## Decision

Add a `ReviewSource` enum (`CARD`, `CHAT`) and a non-null `Review.source` column.
`submit_review` takes a `source` argument; the card path passes `CARD`, the chat
path passes `CHAT`.

**Calibration counts only `source == CARD` reviews** (with a non-null
`predicted_recall`). CHAT reviews are excluded but surfaced to the user as a
coverage count, so the exclusion is transparent rather than silent.

## Consequences

- The dashboard is correct-by-construction: it never mixes approximate data into
  the calibration numbers.
- Because the card player is not currently exposed in the UI, the dashboard will
  usually sit in its honest "not enough data yet" state until either the card flow
  is re-surfaced or the chat attribution is fixed.
- When the tutor path is fixed to attribute outcomes to the real item, CHAT
  reviews can be promoted to trustworthy (or a finer-grained trust flag added)
  without reworking the dashboard.
- No migration tooling exists; the column lands via `create_all` on a fresh DB.
