"""Recommendations service — hybrid engine entry point."""
from sqlalchemy.orm import Session

from api.models import User
from api.modules.recommendations.engine.pipeline import run_recommendation_pipeline


def get_recommendations(db: Session, user: User, limit: int) -> dict:
    """Run multi-stage recommendation pipeline (context → constraints → pools → score → optimize → explain)."""
    return run_recommendation_pipeline(db, user, limit)
