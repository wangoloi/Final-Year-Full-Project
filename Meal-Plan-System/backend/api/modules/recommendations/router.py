"""Recommendations routes - thin layer."""
from fastapi import APIRouter, Depends
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.shared.database import get_db
from api.shared.dependencies import get_current_user
from api.models import User
from api.modules.recommendations.service import get_recommendations
from api.modules.recommendations.feedback_repository import add_feedback
from api.modules.recommendations.engine.pool_cache import cache_stats

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def recommendations(
    limit: int = 12,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Glucose-aware meal guidance and weekly plan (user-facing; scores stay internal)."""
    return get_recommendations(db, user, limit)


@router.get("/engine")
def recommendation_engine_meta(user: User = Depends(get_current_user)):
    """Engine version and in-process pool-cache stats (for ops / UI diagnostics)."""
    return {
        "engine_version": "3.0",
        "cache": cache_stats(),
    }


class FeedbackBody(BaseModel):
    food_id: int
    action: Literal["like", "skip"]


@router.post("/feedback")
def recommendation_feedback(
    body: FeedbackBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record like/skip for lightweight learning (future weight updates)."""
    add_feedback(db, user.id, body.food_id, body.action)
    return {"ok": True}
