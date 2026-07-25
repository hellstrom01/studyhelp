"""Time stats (study & review separation, spec User Stories 32-34).

Computed fresh from session rows every time — never from stored aggregates — so
the displayed numbers can't drift out of sync with reality (the ADR-0002
pattern). "Hours studied" counts only genuine work: study-session work-interval
seconds plus review-session active time (started→ended). Breaks, level checks,
and post-timer card creation never enter a row's counted time, so they are
excluded by construction. Day bucketing is UTC (matching the calibration
dashboard's v1 simplification).
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ReviewSession, StudySession


def _utc_date(dt: datetime) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def _review_active_seconds(rs: ReviewSession) -> int:
    """A review session's active time is started→ended; an unfinished session
    contributes nothing (there is no honest active total yet)."""
    if rs.ended_at is None:
        return 0
    start, end = rs.started_at, rs.ended_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0, int((end - start).total_seconds()))


def compute_stats(
    db: Session, user_id: int, today: date | None = None
) -> dict:
    """Return {hours_studied, streak_days, heatmap} for a user.

    heatmap is [{date: "YYYY-MM-DD", minutes: int}] over days with study time,
    sorted ascending. streak_days is the run of consecutive UTC study days
    ending at (or the day before) `today`.
    """
    today = today or datetime.now(timezone.utc).date()

    study_sessions = list(db.scalars(
        select(StudySession).where(StudySession.user_id == user_id)
    ))
    review_sessions = list(db.scalars(
        select(ReviewSession).where(ReviewSession.user_id == user_id)
    ))

    seconds_by_day: dict[date, int] = {}
    study_days: set[date] = set()

    for ss in study_sessions:
        day = _utc_date(ss.started_at)
        study_days.add(day)
        seconds_by_day[day] = seconds_by_day.get(day, 0) + (ss.work_seconds or 0)

    for rs in review_sessions:
        day = _utc_date(rs.started_at)
        study_days.add(day)
        seconds_by_day[day] = seconds_by_day.get(day, 0) + _review_active_seconds(rs)

    total_seconds = sum(seconds_by_day.values())
    heatmap = [
        {"date": day.isoformat(), "minutes": round(secs / 60)}
        for day, secs in sorted(seconds_by_day.items())
    ]

    return {
        "hours_studied": round(total_seconds / 3600, 2),
        "streak_days": _streak(study_days, today),
        "heatmap": heatmap,
    }


def _streak(study_days: set[date], today: date) -> int:
    """Consecutive study days counting backward. Today not yet being studied is
    grace, not a break: the run may start at today or the day before."""
    if today in study_days:
        cursor = today
    elif (today - timedelta(days=1)) in study_days:
        cursor = today - timedelta(days=1)
    else:
        return 0

    count = 0
    while cursor in study_days:
        count += 1
        cursor -= timedelta(days=1)
    return count
