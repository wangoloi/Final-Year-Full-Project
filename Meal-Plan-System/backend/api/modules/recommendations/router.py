"""Recommendations routes - thin layer."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.shared.database import get_db
from api.shared.dependencies import get_current_user
from api.models import User
from api.modules.recommendations.service import get_recommendations

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def recommendations(
    limit: int = 12,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get personalized food recommendations."""
    recs = get_recommendations(db, user, limit)
    return {"recommendations": recs}
