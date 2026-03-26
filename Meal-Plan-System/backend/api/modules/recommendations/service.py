"""Recommendations service - single responsibility: food recommendations."""
from typing import List
from collections import defaultdict
from sqlalchemy.orm import Session

from api.models import FoodItem, User
from api.modules.recommendations.repository import fetch_candidates
from api.core.logging_config import get_logger

logger = get_logger("api.recommendations.service")


def score_food(food: FoodItem) -> float:
    """Score single food for recommendation."""
    score = 0.0
    if food.glycemic_index is not None:
        if food.glycemic_index <= 40:
            score += 30
        elif food.glycemic_index <= 55:
            score += 20
        else:
            score += 5
    fiber = food.fiber or 0
    if fiber >= 5:
        score += 15
    elif fiber >= 2.5:
        score += 8
    if food.diabetes_friendly:
        score += 10
    return score


def food_to_dict(food: FoodItem) -> dict:
    """Serialize food for response."""
    return {
        "id": str(food.id),
        "name": food.name,
        "local_name": food.local_name,
        "category": food.category,
        "calories": float(food.calories),
        "protein": float(food.protein),
        "carbs": float(food.carbohydrates),
        "fat": float(food.fat),
        "fiber": float(food.fiber or 0),
        "glycemic_index": food.glycemic_index,
        "diabetes_friendly": food.diabetes_friendly,
    }


def diversify_by_category(scored: List[tuple], limit: int) -> List[FoodItem]:
    """Select items ensuring category diversity."""
    by_cat = defaultdict(list)
    for f, s in scored:
        cat = (f.category or "other").lower()
        by_cat[cat].append((f, s))

    result = []
    cats = list(by_cat.keys())
    idx = 0
    while len(result) < limit and any(by_cat[c] for c in cats):
        cat = cats[idx % len(cats)]
        if by_cat[cat]:
            f, _ = by_cat[cat].pop(0)
            result.append(f)
        idx += 1
    return result[:limit]


def get_recommendations(db: Session, user: User, limit: int) -> List[dict]:
    """Get personalized food recommendations."""
    max_gi = 50 if user.has_diabetes else 55
    diabetes_only = user.has_diabetes

    items = fetch_candidates(db, max_gi, diabetes_only, limit * 3)
    if not items and diabetes_only:
        items = fetch_candidates(db, max_gi, False, limit * 3)

    scored = [(f, score_food(f)) for f in items]
    scored.sort(key=lambda x: -x[1])
    diversified = diversify_by_category(scored, limit)

    logger.info("Recommendations generated", extra={"user_id": user.id, "count": len(diversified)})
    return [food_to_dict(f) for f in diversified]
