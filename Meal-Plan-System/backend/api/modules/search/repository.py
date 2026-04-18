"""Search repository - data access for food search."""
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.models import FoodItem
from api.modules.search.query_parser import NutritionFilters


def _apply_nutrition_filters(q, nf: Optional[NutritionFilters]):
    if not nf:
        return q
    if nf.carbs_max is not None:
        q = q.filter(FoodItem.carbohydrates <= float(nf.carbs_max))
    if nf.carbs_min is not None:
        q = q.filter(FoodItem.carbohydrates >= float(nf.carbs_min))
    if nf.sugar_max is not None:
        q = q.filter(FoodItem.sugar <= float(nf.sugar_max))
    if nf.sugar_min is not None:
        q = q.filter(FoodItem.sugar >= float(nf.sugar_min))
    if nf.gi_max is not None:
        q = q.filter(FoodItem.glycemic_index.isnot(None)).filter(FoodItem.glycemic_index <= int(nf.gi_max))
    if nf.gi_min is not None:
        q = q.filter(FoodItem.glycemic_index.isnot(None)).filter(FoodItem.glycemic_index >= int(nf.gi_min))
    return q


def keyword_search(
    db: Session,
    query: str,
    limit: int,
    diabetes_only: bool,
    nf: Optional[NutritionFilters],
    *,
    prefix_only: bool = False,
) -> List[FoodItem]:
    """Search foods by keyword match."""
    q = db.query(FoodItem).filter(
        or_(
            FoodItem.name.ilike(f"{query}%" if prefix_only else f"%{query}%"),
            FoodItem.local_name.ilike(f"{query}%" if prefix_only else f"%{query}%"),
            FoodItem.description.ilike(f"%{query}%") if not prefix_only else False,
            FoodItem.category.ilike(f"%{query}%") if not prefix_only else False,
        )
    )
    if diabetes_only:
        q = q.filter_by(diabetes_friendly=True)
    q = _apply_nutrition_filters(q, nf)
    return q.limit(limit * 2).all()


def fuzzy_search(db: Session, query: str, limit: int, diabetes_only: bool, nf: Optional[NutritionFilters]) -> List[FoodItem]:
    """Search foods by fuzzy match (typos)."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return []

    base_q = db.query(FoodItem)
    if diabetes_only:
        base_q = base_q.filter_by(diabetes_friendly=True)
    base_q = _apply_nutrition_filters(base_q, nf)
    candidates = base_q.all()

    scored = []
    q_lower = query.lower()
    # Tighten fuzzy threshold for short queries to avoid "anything returns results".
    min_score = 0.82 if len(q_lower) <= 3 else 0.55
    for f in candidates:
        name = (f.name or "").lower()
        score = max(
            fuzz.ratio(q_lower, name) / 100,
            fuzz.partial_ratio(q_lower, name) / 100,
        )
        if score >= min_score:
            scored.append((f, score))

    scored.sort(key=lambda x: -x[1])
    return [f for f, _ in scored[:limit]]
