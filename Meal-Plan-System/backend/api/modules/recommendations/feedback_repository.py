"""Stage 6: Feedback counts for lightweight learning."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple

from sqlalchemy.orm import Session

from api.models import UserFoodFeedback


def get_like_avoid_counts(db: Session, user_id: int) -> Tuple[Dict[int, int], Dict[int, int]]:
    rows = db.query(UserFoodFeedback).filter_by(user_id=user_id).all()
    liked: Dict[int, int] = defaultdict(int)
    avoided: Dict[int, int] = defaultdict(int)
    for r in rows:
        if r.action == "like":
            liked[r.food_id] += 1
        elif r.action == "skip":
            avoided[r.food_id] += 1
    return dict(liked), dict(avoided)


def add_feedback(db: Session, user_id: int, food_id: int, action: str) -> None:
    if action not in ("like", "skip"):
        raise ValueError("action must be like or skip")
    db.add(UserFoodFeedback(user_id=user_id, food_id=food_id, action=action))
    db.commit()
