"""Tests for the stats service (the agreed service-function seam).

Time stats are computed fresh from session rows — never from stored aggregates,
so displayed numbers can't drift (the ADR-0002 pattern). Hours studied counts
only real work: study-session work-interval seconds plus review-session active
time. Breaks, level checks, and post-timer card creation never land in a row's
counted time, so they are excluded by construction. Days bucket by UTC.
"""

from datetime import date, datetime, timedelta, timezone

from studyhelp.models import ReviewSession, StudySession
from studyhelp.stats import compute_stats

DAY = datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc)


def _study(user_id, subject_id, started, work_seconds):
    return StudySession(
        user_id=user_id, subject_id=subject_id,
        started_at=started, ended_at=started + timedelta(minutes=30),
        work_seconds=work_seconds,
    )


def _review(user_id, started, active_seconds):
    return ReviewSession(
        user_id=user_id, started_at=started,
        ended_at=started + timedelta(seconds=active_seconds),
    )


def test_hours_studied_sums_study_work_and_review_active_time(db, seed):
    subj = seed.subject()
    db.add(_study(seed.user.id, subj.id, DAY, work_seconds=45 * 60))
    db.add(_review(seed.user.id, DAY, active_seconds=15 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    # 45 min work + 15 min review = 1.0 hour
    assert out["hours_studied"] == 1.0


def test_unfinished_review_session_contributes_no_active_time(db, seed):
    seed.subject()
    rs = ReviewSession(user_id=seed.user.id, started_at=DAY, ended_at=None)
    db.add(rs)
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["hours_studied"] == 0.0


def test_heatmap_buckets_minutes_by_utc_day(db, seed):
    subj = seed.subject()
    db.add(_study(seed.user.id, subj.id, DAY, work_seconds=20 * 60))
    db.add(_study(seed.user.id, subj.id, DAY + timedelta(hours=2), work_seconds=10 * 60))
    db.add(_study(seed.user.id, subj.id, DAY + timedelta(days=1), work_seconds=5 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=(DAY + timedelta(days=1)).date())
    heat = {h["date"]: h["minutes"] for h in out["heatmap"]}
    assert heat["2026-07-20"] == 30
    assert heat["2026-07-21"] == 5


def test_streak_counts_consecutive_days_including_today(db, seed):
    subj = seed.subject()
    for offset in (0, 1, 2):  # today, yesterday, day before
        db.add(_study(seed.user.id, subj.id, DAY - timedelta(days=offset),
                      work_seconds=10 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["streak_days"] == 3


def test_streak_survives_today_being_unstudied(db, seed):
    # Studied yesterday and the day before but not yet today: the streak is still
    # alive (counted from yesterday), not reset to zero.
    subj = seed.subject()
    for offset in (1, 2):
        db.add(_study(seed.user.id, subj.id, DAY - timedelta(days=offset),
                      work_seconds=10 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["streak_days"] == 2


def test_streak_breaks_on_a_gap(db, seed):
    subj = seed.subject()
    # today and 3 days ago — the two-day gap breaks the run at 1
    db.add(_study(seed.user.id, subj.id, DAY, work_seconds=10 * 60))
    db.add(_study(seed.user.id, subj.id, DAY - timedelta(days=3), work_seconds=10 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["streak_days"] == 1


def test_streak_is_zero_when_no_recent_activity(db, seed):
    subj = seed.subject()
    db.add(_study(seed.user.id, subj.id, DAY - timedelta(days=5), work_seconds=10 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["streak_days"] == 0


def test_single_study_day_today_is_a_streak_of_one(db, seed):
    subj = seed.subject()
    db.add(_study(seed.user.id, subj.id, DAY, work_seconds=10 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["streak_days"] == 1


def test_review_only_day_still_counts_as_a_study_day(db, seed):
    # A study day is any day with a study OR review session (CONTEXT.md).
    seed.subject()
    db.add(_review(seed.user.id, DAY, active_seconds=10 * 60))
    db.commit()

    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["streak_days"] == 1


def test_empty_history_is_honest_zeroes(db, seed):
    seed.subject()
    out = compute_stats(db, seed.user.id, today=DAY.date())
    assert out["hours_studied"] == 0.0
    assert out["streak_days"] == 0
    assert out["heatmap"] == []
