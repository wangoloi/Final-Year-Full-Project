"""Glucose repository - data access for glucose readings."""
from typing import List
from sqlalchemy.orm import Session

from api.models import GlucoseReading


VALID_TYPES = ("fasting", "pre_meal", "post_meal", "random")


def normalize_reading_type(reading_type: str) -> str:
    """Return valid reading type or default."""
    if reading_type in VALID_TYPES:
        return reading_type
    return "random"


def list_readings(db: Session, user_id: int, limit: int) -> List[GlucoseReading]:
    """List user's glucose readings."""
    return (
        db.query(GlucoseReading)
        .filter_by(user_id=user_id)
        .order_by(GlucoseReading.reading_time.desc())
        .limit(limit)
        .all()
    )
