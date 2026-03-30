"""Seed utilities - single responsibility: load initial data."""
import csv
from pathlib import Path
from sqlalchemy.orm import Session

from api.models import FoodItem
from api.core.logging_config import get_logger

logger = get_logger("api.seed")


def _csv_path() -> Path:
    return Path(__file__).resolve().parents[2] / "datasets" / "uganda_food_nutrition_dataset(in).csv"


def _row_to_food(row: dict) -> FoodItem | None:
    """Convert CSV row to FoodItem. Returns None if row invalid."""
    name = row.get("food_name") or row.get("name")
    if not name or not str(name).strip():
        return None

    return FoodItem(
        name=str(name).strip(),
        local_name=(row.get("local_name") or "").strip() or None,
        category=(row.get("category") or "other").strip().lower(),
        description=(row.get("description") or "").strip() or None,
        calories=float(row.get("calories", 0) or 0),
        protein=float(row.get("protein", 0) or 0),
        carbohydrates=float(row.get("carbohydrates", 0) or 0),
        fiber=float(row.get("fiber", 0) or 0),
        fat=float(row.get("fat", 0) or 0),
        sugar=float(row.get("sugar", 0) or 0),
        glycemic_index=_parse_int(row.get("glycemic_index")),
        diabetes_friendly=_parse_bool(row.get("diabetes_friendly", "true")),
        serving_size=(row.get("serving_size") or "").strip() or None,
    )


def _parse_int(val) -> int | None:
    if val in ("", None):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _parse_bool(val) -> bool:
    return str(val).lower() in ("true", "1", "yes")


def load_foods_from_csv(db: Session) -> int:
    """Load foods from CSV. Returns count loaded."""
    path = _csv_path()
    if not path.exists():
        logger.warning("CSV not found", extra={"path": str(path)})
        return 0

    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            food = _row_to_food(row)
            if not food:
                continue
            if db.query(FoodItem).filter_by(name=food.name).first():
                continue
            db.add(food)
            count += 1

    if count > 0:
        db.commit()
        logger.info("Foods loaded from CSV", extra={"count": count})
    return count


def seed_fallback(db: Session) -> None:
    """Seed minimal fallback if CSV missing."""
    if db.query(FoodItem).first():
        return

    fallback = [
        {"name": "Apple", "local_name": "Apuro", "category": "fruits", "calories": 52, "protein": 0.3,
         "carbohydrates": 13.8, "fiber": 2.4, "fat": 0.2, "sugar": 10.4, "glycemic_index": 36, "diabetes_friendly": True},
        {"name": "Matooke", "local_name": "Matooke", "category": "grains", "calories": 122, "protein": 1.3,
         "carbohydrates": 31.9, "fiber": 2.3, "fat": 0.4, "sugar": 15, "glycemic_index": 45, "diabetes_friendly": True},
    ]
    for d in fallback:
        db.add(FoodItem(**d))
    db.commit()
    logger.info("Fallback foods seeded")


def build_rag_store(db: Session) -> None:
    """Build Chroma vector index over foods for chatbot RAG (best-effort)."""
    try:
        import chromadb  # noqa: F401 — declared in backend/requirements.txt
    except ImportError:
        logger.warning(
            "Chatbot RAG skipped: chromadb is not installed. "
            "From Meal-Plan-System/backend run: pip install -r requirements.txt"
        )
        return
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401 — must match huggingface_hub (use v3+)
    except ImportError as e:
        logger.warning(
            "Chatbot RAG skipped: sentence-transformers missing or incompatible with huggingface_hub (%s). "
            "From Meal-Plan-System/backend: pip install -U \"sentence-transformers>=3.0.0,<4\"",
            e,
        )
        return
    try:
        from api.modules.chatbot.rag_store import rebuild_rag_index

        n = rebuild_rag_index()
        if n:
            logger.info("Chatbot RAG index built", extra={"documents": n})
    except Exception as e:
        logger.warning("Chatbot RAG index build failed (chatbot falls back to rules or LLM without vectors)", extra={"error": str(e)})


def _food_to_doc(f: FoodItem) -> str:
    """Convert food to document string."""
    return f"{f.name} ({f.local_name or ''}): {f.category}. Calories: {f.calories}, Carbs: {f.carbohydrates}g, glycemic index: {f.glycemic_index or 'N/A'}. Diabetes-friendly: {f.diabetes_friendly}."
