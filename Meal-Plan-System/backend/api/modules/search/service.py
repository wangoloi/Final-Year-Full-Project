"""Search service - Typesense when configured; otherwise SQL keyword + RapidFuzz."""
from typing import List
from sqlalchemy.orm import Session

from api.models import FoodItem
from api.modules.search.repository import keyword_search, fuzzy_search
from api.modules.search import typesense_search
from api.core.logging_config import get_logger

logger = get_logger("api.search.service")


def search_foods(db: Session, query: str, limit: int, diabetes_only: bool) -> List[dict]:
    """
    Search foods. Returns API-shaped dicts (same keys as /api/search).
    Uses Typesense when TYPESENSE_HOST is set; falls back to SQL on error or when disabled.
    """
    q = (query or "").strip()
    if not q:
        return []

    if typesense_search.is_typesense_configured():
        try:
            results = typesense_search.search_foods_typesense(q, limit, diabetes_only)
            logger.info("Search completed (Typesense)", extra={"query": q, "count": len(results)})
            return results
        except Exception as e:
            logger.warning("Typesense search failed, using SQL fallback", extra={"error": str(e)})

    results = keyword_search(db, q, limit, diabetes_only)
    if not results:
        results = fuzzy_search(db, q, limit, diabetes_only)
    logger.info("Search completed (SQL)", extra={"query": q, "count": len(results)})
    return [food_to_response(f) for f in results[:limit]]


def food_to_response(food: FoodItem) -> dict:
    """Serialize food for API response."""
    return {
        "id": food.id,
        "name": food.name,
        "local_name": food.local_name,
        "category": food.category,
        "calories": food.calories,
        "glycemic_index": food.glycemic_index,
        "diabetes_friendly": food.diabetes_friendly,
        "carbohydrates": food.carbohydrates,
        "protein": food.protein,
        "fat": food.fat,
        "fiber": food.fiber,
    }
