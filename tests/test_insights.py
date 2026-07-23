"""Tests for the calibration service (the single agreed seam).

Everything is driven by seeding Review rows directly — no HTTP, no LLM, no FSRS.
Asserts only the external payload of compute_calibration.
"""

from datetime import timedelta

import pytest

from studyhelp.insights import compute_calibration
from studyhelp.models import ReviewSource
from tests.conftest import BASE_DAY


def test_no_reviews_is_honest_empty_state(db, seed):
    seed.subject()
    out = compute_calibration(db, seed.user.id)

    assert out["coverage"]["trustworthy_count"] == 0
    assert out["coverage"]["excluded_chat_count"] == 0
    assert out["coverage"]["threshold_met"] is False
    assert out["curve"] == []
    assert out["trend"] == []
    assert out["headline"] is None
    assert out["bias"] is None
    assert out["bias_label"] is None


def test_below_threshold_returns_no_charts(db, seed):
    subj = seed.subject()
    seed.add_many(subj, 0.85, n_correct=8, n_wrong=2)  # only 10 trustworthy

    out = compute_calibration(db, seed.user.id)

    assert out["coverage"]["trustworthy_count"] == 10
    assert out["coverage"]["threshold_met"] is False
    assert out["curve"] == []
    assert out["trend"] == []
    assert out["headline"] is None


def test_chat_reviews_are_excluded_and_counted(db, seed):
    subj = seed.subject()
    # 20 trustworthy CARD reviews, perfectly calibrated at 0.85
    seed.add_many(subj, 0.85, n_correct=17, n_wrong=3)
    # noisy CHAT reviews that must not affect any number
    seed.add_many(subj, 0.05, n_correct=0, n_wrong=5, source=ReviewSource.CHAT)

    out = compute_calibration(db, seed.user.id)

    assert out["coverage"]["trustworthy_count"] == 20
    assert out["coverage"]["excluded_chat_count"] == 5
    assert out["coverage"]["threshold_met"] is True
    # headline reflects only the CARD reviews
    assert out["headline"] == pytest.approx((17 * 0.15 + 3 * 0.85) / 20)


def test_card_review_with_null_prediction_is_not_trustworthy(db, seed):
    subj = seed.subject()
    seed.add_many(subj, 0.85, n_correct=18, n_wrong=2)  # 20 usable
    seed.add(subj, None, True)  # CARD but no prediction -> not counted

    out = compute_calibration(db, seed.user.id)
    assert out["coverage"]["trustworthy_count"] == 20


def test_reliability_curve_bins_and_bias(db, seed):
    subj = seed.subject()
    # all predictions land in the [0.8, 0.9) decile; 17/20 correct -> actual 0.85
    seed.add_many(subj, 0.85, n_correct=17, n_wrong=3)

    out = compute_calibration(db, seed.user.id)

    assert len(out["curve"]) == 1
    b = out["curve"][0]
    assert b["bin_low"] == pytest.approx(0.8)
    assert b["bin_high"] == pytest.approx(0.9)
    assert b["mean_predicted"] == pytest.approx(0.85)
    assert b["actual_accuracy"] == pytest.approx(0.85)
    assert b["n"] == 20
    # predicted 0.85 vs actual 0.85 -> essentially unbiased
    assert out["bias"] == pytest.approx(0.0, abs=1e-9)
    assert out["bias_label"] == "well calibrated"


def test_small_bins_are_omitted(db, seed):
    subj = seed.subject()
    seed.add_many(subj, 0.85, n_correct=16, n_wrong=4)   # 20 in [0.8,0.9)
    seed.add_many(subj, 0.15, n_correct=2, n_wrong=1)    # only 3 in [0.1,0.2)

    out = compute_calibration(db, seed.user.id)

    assert out["coverage"]["trustworthy_count"] == 23
    # the 3-review bin is below the per-bin floor and must not be plotted
    assert len(out["curve"]) == 1
    assert out["curve"][0]["bin_low"] == pytest.approx(0.8)


def test_overconfident_bias(db, seed):
    subj = seed.subject()
    seed.add_many(subj, 0.9, n_correct=5, n_wrong=15)  # predicts 0.9, actual 0.25

    out = compute_calibration(db, seed.user.id)
    assert out["bias"] == pytest.approx(0.9 - 0.25)
    assert out["bias_label"] == "overconfident"


def test_underconfident_bias(db, seed):
    subj = seed.subject()
    seed.add_many(subj, 0.4, n_correct=18, n_wrong=2)  # predicts 0.4, actual 0.9

    out = compute_calibration(db, seed.user.id)
    assert out["bias"] == pytest.approx(0.4 - 0.9)
    assert out["bias_label"] == "underconfident"


def test_trend_buckets_by_utc_day(db, seed):
    subj = seed.subject()
    day1 = BASE_DAY
    day2 = BASE_DAY + timedelta(days=1)
    # 12 reviews on day1, 10 on day2 (>= 20 total, passes threshold)
    seed.add_many(subj, 0.8, n_correct=9, n_wrong=3, when=day1)
    seed.add_many(subj, 0.8, n_correct=5, n_wrong=5, when=day2)

    out = compute_calibration(db, seed.user.id)
    trend = out["trend"]

    assert [p["date"] for p in trend] == ["2026-07-01", "2026-07-02"]
    assert trend[0]["n"] == 12
    assert trend[1]["n"] == 10
    # day1: |0.8-1|*9 + |0.8-0|*3 = 1.8 + 2.4 = 4.2 over 12
    assert trend[0]["mean_abs_error"] == pytest.approx(4.2 / 12)


def test_subject_filter_scopes_everything(db, seed):
    a = seed.subject("A")
    b = seed.subject("B")
    seed.add_many(a, 0.9, n_correct=20, n_wrong=0)   # perfect-ish in A
    seed.add_many(b, 0.9, n_correct=0, n_wrong=20)   # terrible in B

    only_a = compute_calibration(db, seed.user.id, subject_id=a.id)
    only_b = compute_calibration(db, seed.user.id, subject_id=b.id)
    combined = compute_calibration(db, seed.user.id)

    assert only_a["coverage"]["trustworthy_count"] == 20
    assert only_b["coverage"]["trustworthy_count"] == 20
    assert combined["coverage"]["trustworthy_count"] == 40
    # A is underconfident-ish? predicted 0.9 actual 1.0 -> bias negative
    assert only_a["bias"] == pytest.approx(0.9 - 1.0)
    assert only_b["bias"] == pytest.approx(0.9 - 0.0)
