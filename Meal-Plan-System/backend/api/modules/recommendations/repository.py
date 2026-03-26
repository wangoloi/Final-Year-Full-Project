"""Recommendations repository - data access for food recommendations."""
from typing import List
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.models import FoodItem, User


def fetch_candidates(db: Session, max_gi: int, diabetes_only: bool, limit: int) -> List[FoodItem]:
    """Fetch food candidates for recommendations."""
    q = db.query(FoodItem).filter(
        or_(FoodItem.glycemic_index.is_(None), FoodItem.glycemic_index <= max_gi)
    )
    if diabetes_only:
        q = q.filter_by(diabetes_friendly=True)
    return q.order_by(FoodItem.glycemic_index.asc(), FoodItem.fiber.desc()).limit(limit).all()
