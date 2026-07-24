# ADR-0002: Compute calibration fresh from reviews, not from the stored session value

Status: Accepted (2026-07-23)

## Context

`StudySession.avg_calibration_error` is written by `end_session`, which averages
`|predicted_recall - actual|` over every review in the session's time window —
regardless of source. With the trust policy in ADR-0001, that stored value mixes
trustworthy (CARD) and untrustworthy (CHAT) reviews, so it cannot be shown as a
calibration metric.

## Decision

The calibration service (`insights.compute_calibration`) reads `Review` rows
directly, filters to trustworthy reviews, and computes the headline, bias,
reliability curve, and daily trend on the fly. It does **not** read
`StudySession.avg_calibration_error`.

Data volumes are tiny (single user, SQLite), so on-the-fly computation is simple
and fast; there is no aggregation table to maintain or keep in sync.

## Consequences

- One source of truth for calibration numbers, always consistent with the current
  trust policy and filters (including the per-course filter).
- `StudySession.avg_calibration_error` is now effectively legacy. It is left in
  place (still written by the legacy card-session `end_session`) but is not used
  by the dashboard. A future cleanup may remove or repurpose it.
- All calibration logic lives behind a single, directly testable function seam.
