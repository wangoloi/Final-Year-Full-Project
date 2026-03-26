"""Search repository - data access for food search."""
from typing import List
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.models import FoodItem


def keyword_search(db: Session, query: str, limit: int, diabetes_only: bool) -> List[FoodItem]:
    """Search foods by keyword match."""
    q = db.query(FoodItem).filter(
        or_(
            FoodItem.name.ilike(f"%{query}%"),
            FoodItem.local_name.ilike(f"%{query}%"),
            FoodItem.description.ilike(f"%{query}%"),
            FoodItem.category.ilike(f"%{query}%"),
        )
    )
    if diabetes_only:
        q = q.filter_by(diabetes_friendly=True)
    return q.limit(limit * 2).all()


def fuzzy_search(db: Session, query: str, limit: int, diabetes_only: bool) -> List[FoodItem]:
    """Search foods by fuzzy match (typos)."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return []

    candidates = db.query(FoodItem).all()
    if diabetes_only:
        candidates = [c for c in candidates if c.diabetes_friendly]

    scored = []
    q_lower = query.lower()
    for f in candidates:
        name = (f.name or "").lower()
        score = max(
            fuzz.ratio(q_lower, name) / 100,
            fuzz.partial_ratio(q_lower, name) / 100,
        )
        if score >= 0.5:
            scored.append((f, score))

    scored.sort(key=lambda x: -x[1])
    return [f for f, _ in scored[:limit]]
