"""
Typesense-backed food search (typo-tolerant, multi-field). Falls back to SQL when disabled or on error.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List

from api.core import config
from api.models import FoodItem
from api.shared.database import SessionLocal

logger = logging.getLogger(__name__)

try:
    import typesense
except ImportError:
    typesense = None  # type: ignore


def is_typesense_configured() -> bool:
    return bool(typesense and config.TYPESENSE_HOST)


def _client():
    if not is_typesense_configured():
        raise RuntimeError("Typesense not configured")
    return typesense.Client(
        {
            "nodes": [
                {
                    "host": config.TYPESENSE_HOST,
                    "port": str(config.TYPESENSE_PORT),
                    "protocol": config.TYPESENSE_PROTOCOL,
                }
            ],
            "api_key": config.TYPESENSE_API_KEY,
            "connection_timeout_seconds": 8,
        }
    )


def _collection_schema() -> dict:
    name = config.TYPESENSE_FOODS_COLLECTION
    return {
        "name": name,
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "name", "type": "string"},
            {"name": "local_name", "type": "string", "optional": True},
            {"name": "category", "type": "string"},
            {"name": "description", "type": "string", "optional": True},
            {"name": "calories", "type": "float"},
            {"name": "protein", "type": "float"},
            {"name": "carbohydrates", "type": "float"},
            {"name": "fat", "type": "float"},
            {"name": "fiber", "type": "float"},
            {"name": "glycemic_index", "type": "int32", "optional": True},
            {"name": "diabetes_friendly", "type": "bool", "facet": True},
        ],
    }


def ensure_foods_collection() -> None:
    """Create the foods collection if it does not exist."""
    client = _client()
    name = config.TYPESENSE_FOODS_COLLECTION
    try:
        client.collections[name].retrieve()
        return
    except Exception:
        pass
    try:
        client.collections.create(_collection_schema())
        logger.info("Typesense collection created", extra={"collection": name})
    except Exception as e:
        err = str(e).lower()
        if "already exists" in err or "duplicate" in err:
            return
        raise


def _food_to_document(food: FoodItem) -> dict:
    doc: dict[str, Any] = {
        "id": str(food.id),
        "name": food.name or "",
        "local_name": food.local_name or "",
        "category": food.category or "",
        "description": (food.description or "")[: 8000],
        "calories": float(food.calories),
        "protein": float(food.protein),
        "carbohydrates": float(food.carbohydrates),
        "fat": float(food.fat),
        "fiber": float(food.fiber),
        "diabetes_friendly": bool(food.diabetes_friendly),
    }
    if food.glycemic_index is not None:
        doc["glycemic_index"] = int(food.glycemic_index)
    return doc


def document_to_api_dict(doc: dict) -> dict:
    """Match public API shape from /api/search."""
    gid = doc.get("glycemic_index")
    return {
        "id": int(doc["id"]) if str(doc.get("id", "")).isdigit() else doc.get("id"),
        "name": doc.get("name", ""),
        "local_name": doc.get("local_name") or None,
        "category": doc.get("category", ""),
        "description": doc.get("description"),
        "calories": float(doc.get("calories", 0)),
        "glycemic_index": int(gid) if gid is not None else None,
        "diabetes_friendly": bool(doc.get("diabetes_friendly", False)),
        "carbohydrates": float(doc.get("carbohydrates", 0)),
        "protein": float(doc.get("protein", 0)),
        "fat": float(doc.get("fat", 0)),
        "fiber": float(doc.get("fiber", 0)),
    }


def sync_foods_index_from_db() -> int:
    """
    Upsert all foods from SQLite into Typesense.
    Call after DB seed or when rebuilding the index.
    """
    if not is_typesense_configured():
        return 0
    db = SessionLocal()
    try:
        foods = db.query(FoodItem).order_by(FoodItem.id).all()
        if not foods:
            return 0
        ensure_foods_collection()
        client = _client()
        coll = client.collections[config.TYPESENSE_FOODS_COLLECTION]
        lines = [json.dumps(_food_to_document(f)) for f in foods]
        import_res = coll.documents.import_("\n".join(lines), {"action": "upsert"})
        if isinstance(import_res, str):
            for line in import_res.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if row.get("success") is False:
                        logger.warning("Typesense doc import line failed", extra={"row": row})
                except json.JSONDecodeError:
                    pass
        return len(foods)
    finally:
        db.close()


def search_foods_typesense(query: str, limit: int, diabetes_only: bool) -> List[dict]:
    """Search foods via Typesense; returns API-shaped dicts."""
    q = (query or "").strip()
    if not q:
        return []
    ensure_foods_collection()
    client = _client()
    coll = client.collections[config.TYPESENSE_FOODS_COLLECTION]
    params: dict[str, Any] = {
        "q": q,
        "query_by": "name,local_name,description,category",
        "per_page": limit,
        "num_typos": 2,
    }
    if diabetes_only:
        params["filter_by"] = "diabetes_friendly:=true"
    res = coll.documents.search(params)
    hits = res.get("hits") or []
    out: List[dict] = []
    for h in hits:
        doc = h.get("document") or {}
        out.append(document_to_api_dict(doc))
    return out
