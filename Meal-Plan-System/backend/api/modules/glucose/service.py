"""Glucose service - single responsibility: glucose CRUD."""
from sqlalchemy.orm import Session

from api.models import GlucoseReading
from api.modules.glucose.repository import normalize_reading_type, list_readings
from api.core.logging_config import get_logger

logger = get_logger("api.glucose.service")


def reading_to_dict(r: GlucoseReading) -> dict:
    """Serialize reading for response."""
    return {
        "id": r.id,
        "reading_value": r.reading_value,
        "reading_type": r.reading_type,
        "reading_time": r.reading_time.isoformat(),
        "notes": r.notes,
    }


def add_reading(db: Session, user_id: int, value: float, reading_type: str, notes: str) -> GlucoseReading:
    """Add glucose reading."""
    rt = normalize_reading_type(reading_type)
    r = GlucoseReading(user_id=user_id, reading_value=value, reading_type=rt, notes=notes)
    db.add(r)
    db.commit()
    db.refresh(r)
    logger.info("Glucose reading added", extra={"user_id": user_id})
    return r


def get_readings(db: Session, user_id: int, limit: int = 100) -> list:
    """Get user's glucose readings."""
    rows = list_readings(db, user_id, limit)
    return [reading_to_dict(r) for r in rows]
