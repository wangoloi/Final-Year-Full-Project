"""Search service - Typesense when configured; otherwise SQL keyword + RapidFuzz."""
from typing import List
from sqlalchemy.orm import Session

from api.models import FoodItem
from api.modules.search.repository import keyword_search, fuzzy_search
from api.modules.search import typesense_search
from api.modules.search.query_parser import parse_search_query
from api.core.logging_config import get_logger

logger = get_logger("api.search.service")


def search_foods(db: Session, query: str, limit: int, diabetes_only: bool) -> List[dict]:
    """
    Search foods. Returns API-shaped dicts (same keys as /api/search).
    Uses Typesense when TYPESENSE_HOST is set; falls back to SQL on error or when disabled.
    """
    q_raw = (query or "").strip()
    if not q_raw:
        return []
    # Parse "low carb", "high GI", etc into numeric filters; keep remaining text.
    text_q, nf = parse_search_query(q_raw)
    q = text_q or q_raw
    # For the main search endpoint, avoid returning everything for 1-char queries.
    if len(q.strip()) < 2:
        return []

    if typesense_search.is_typesense_configured():
        try:
            results = typesense_search.search_foods_typesense(
                q, limit, diabetes_only, filters=nf.__dict__
            )
            logger.info(
                "Search completed (Typesense)",
                extra={"query": q_raw, "text_query": q, "count": len(results), "filters": nf.__dict__},
            )
            return results
        except Exception as e:
            logger.warning("Typesense search failed, using SQL fallback", extra={"error": str(e)})

    results = keyword_search(db, q, limit, diabetes_only, nf)
    if not results:
        results = fuzzy_search(db, q, limit, diabetes_only, nf)
    logger.info("Search completed (SQL)", extra={"query": q_raw, "text_query": q, "count": len(results), "filters": nf.__dict__})
    return [food_to_response(f) for f in results[:limit]]


def suggest_foods(db: Session, prefix: str, limit: int, diabetes_only: bool) -> List[dict]:
    """Autocomplete suggestions (no filters; prefix search only)."""
    p = (prefix or "").strip()
    if not p or len(p) < 1:
        return []
    if typesense_search.is_typesense_configured():
        try:
            return typesense_search.suggest_foods_typesense(p, limit, diabetes_only)
        except Exception as e:
            logger.warning("Typesense suggest failed, using SQL fallback", extra={"error": str(e)})
    # SQL fallback: startswith-like matches on name/local_name
    results = keyword_search(db, p, limit, diabetes_only, None, prefix_only=True)
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
