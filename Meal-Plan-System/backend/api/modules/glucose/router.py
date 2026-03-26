"""Glucose routes - thin layer."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from api.shared.database import get_db
from api.shared.dependencies import get_current_user
from api.models import User
from api.modules.glucose.service import add_reading, get_readings, reading_to_dict

router = APIRouter(prefix="/api/glucose", tags=["glucose"])


class GlucoseInput(BaseModel):
    reading_value: float
    reading_type: str = "random"
    notes: Optional[str] = None


@router.get("")
def glucose_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List glucose readings."""
    return {"readings": get_readings(db, user.id)}


@router.post("")
def glucose_add(
    data: GlucoseInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add glucose reading."""
    r = add_reading(db, user.id, data.reading_value, data.reading_type, data.notes)
    return {"reading": reading_to_dict(r)}
