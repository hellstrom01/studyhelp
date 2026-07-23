"""Insights API — calibration (predicted vs actual recall)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..insights import compute_calibration
from ..models import User
from ..schemas import CalibrationOut

router = APIRouter(prefix="/users/{user_id}/insights", tags=["insights"])


@router.get("/calibration", response_model=CalibrationOut)
def calibration(
    user_id: int,
    subject_id: int | None = None,
    db: DBSession = Depends(get_db),
):
    """Calibration payload, optionally scoped to a single course (subject)."""
    if db.get(User, user_id) is None:
        raise HTTPException(404, f"User {user_id} not found")
    return compute_calibration(db, user_id, subject_id)
