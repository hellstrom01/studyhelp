"""Calibration insights (spec Part 4/5.6).

Computes predicted-vs-actual recall from trustworthy review data. Everything the
dashboard shows comes from `compute_calibration` — a single read-only seam so the
logic can be tested without the web or LLM layers.

Trust policy (ADR-0001): only reviews whose prediction and outcome provably refer
to the same item are counted — carried by the `attribution_exact` flag (true for
CARD reviews and for CHAT reviews resolved to the item actually quizzed). Legacy
approximate CHAT reviews are excluded (but reported as coverage). We compute fresh
from the reviews and never read LegacySession.avg_calibration_error (ADR-0002).
"""

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BiasLabel, Item, Review, ReviewSource, Subject, Topic

# Honesty guards: below these, we refuse to draw a misleading chart.
MIN_TRUSTWORTHY = 20   # overall floor before any charts render
MIN_BIN = 5            # per-bin floor before a curve point is plotted
NUM_BINS = 10          # deciles over [0, 1]
BIAS_EPS = 0.05        # |bias| under this reads as "well calibrated"


def _is_trustworthy(review) -> bool:
    """A review counts toward calibration when its prediction and outcome refer
    to the same item (attribution_exact) and a prediction was recorded."""
    return review.attribution_exact is True and review.predicted_recall is not None


def _utc_date_str(dt):
    """ISO date (YYYY-MM-DD) of a timestamp, normalised to UTC."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.date().isoformat()


def _empty(trustworthy_count: int, excluded_chat_count: int) -> dict:
    return {
        "headline": None,
        "bias": None,
        "bias_label": None,
        "curve": [],
        "trend": [],
        "coverage": {
            "trustworthy_count": trustworthy_count,
            "excluded_chat_count": excluded_chat_count,
            "threshold_met": False,
            "min_trustworthy": MIN_TRUSTWORTHY,
        },
    }


def compute_calibration(db: Session, user_id: int, subject_id: int | None = None) -> dict:
    """Return the calibration payload for a user, optionally scoped to a course.

    Payload:
        headline    overall mean |predicted - actual|, or None below threshold
        bias        signed mean (predicted - actual); + overconfident, or None
        bias_label  "overconfident" | "underconfident" | "well calibrated" | None
        curve       [{bin_low, bin_high, mean_predicted, actual_accuracy, n}]
        trend       [{date, mean_abs_error, n}] sorted by UTC day
        coverage    {trustworthy_count, excluded_chat_count, threshold_met}
    """
    q = (
        select(Review)
        .join(Item, Review.item_id == Item.id)
        .join(Topic, Item.topic_id == Topic.id)
        .join(Subject, Topic.subject_id == Subject.id)
        .where(Subject.user_id == user_id)
    )
    if subject_id is not None:
        q = q.where(Subject.id == subject_id)

    reviews = list(db.scalars(q))

    trustworthy = [r for r in reviews if _is_trustworthy(r)]
    # Chat reviews that did NOT count: legacy/approximate rows whose prediction
    # and outcome may refer to different items. Reported so exclusion is visible.
    excluded_chat_count = sum(
        1 for r in reviews
        if r.source == ReviewSource.CHAT and not _is_trustworthy(r)
    )

    if len(trustworthy) < MIN_TRUSTWORTHY:
        return _empty(len(trustworthy), excluded_chat_count)

    # Pair each review as (predicted, actual, day).
    pairs = [
        (r.predicted_recall, 1.0 if r.was_correct else 0.0, _utc_date_str(r.reviewed_at))
        for r in trustworthy
    ]

    abs_errors = [abs(p - a) for p, a, _ in pairs]
    headline = sum(abs_errors) / len(abs_errors)

    bias = sum(p - a for p, a, _ in pairs) / len(pairs)
    if bias > BIAS_EPS:
        bias_label = BiasLabel.OVERCONFIDENT
    elif bias < -BIAS_EPS:
        bias_label = BiasLabel.UNDERCONFIDENT
    else:
        bias_label = BiasLabel.WELL_CALIBRATED

    curve = _build_curve(pairs)
    trend = _build_trend(pairs)

    return {
        "headline": headline,
        "bias": bias,
        "bias_label": bias_label,
        "curve": curve,
        "trend": trend,
        "coverage": {
            "trustworthy_count": len(trustworthy),
            "excluded_chat_count": excluded_chat_count,
            "threshold_met": True,
            "min_trustworthy": MIN_TRUSTWORTHY,
        },
    }


def _build_curve(pairs: list[tuple[float, float, str]]) -> list[dict]:
    """Bin predictions into deciles; emit only bins meeting the per-bin floor."""
    buckets: list[list[tuple[float, float]]] = [[] for _ in range(NUM_BINS)]
    for predicted, actual, _ in pairs:
        idx = min(int(predicted * NUM_BINS), NUM_BINS - 1)
        buckets[idx].append((predicted, actual))

    curve = []
    for idx, bucket in enumerate(buckets):
        if len(bucket) < MIN_BIN:
            continue
        n = len(bucket)
        curve.append({
            "bin_low": idx / NUM_BINS,
            "bin_high": (idx + 1) / NUM_BINS,
            "mean_predicted": sum(p for p, _ in bucket) / n,
            "actual_accuracy": sum(a for _, a in bucket) / n,
            "n": n,
        })
    return curve


def _build_trend(pairs: list[tuple[float, float, str]]) -> list[dict]:
    """Mean absolute calibration error per UTC calendar day."""
    by_day: dict[str, list[float]] = {}
    for predicted, actual, day in pairs:
        by_day.setdefault(day, []).append(abs(predicted - actual))

    return [
        {"date": day, "mean_abs_error": sum(errs) / len(errs), "n": len(errs)}
        for day, errs in sorted(by_day.items())
    ]
