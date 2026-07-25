"""Time-stats API — hours studied, streak, and a per-day minutes heatmap.

Computed fresh from session rows on every request (ADR-0002 pattern).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models import User
from ..schemas import StatsOut
from ..stats import compute_stats

router = APIRouter(prefix="/users/{user_id}/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def stats(user_id: int, db: DBSession = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise HTTPException(404, f"User {user_id} not found")
    return compute_stats(db, user_id)
