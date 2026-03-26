"""
Chroma + sentence-transformers vector store over food items (RAG retrieval).
"""
from __future__ import annotations

import logging
from typing import List

from api.core import config
from api.models import FoodItem
from api.shared.database import SessionLocal

logger = logging.getLogger(__name__)

_client = None
_ef = None


def _food_document(f: FoodItem) -> str:
    parts = [
        f"Food: {f.name}",
        f"Local name: {f.local_name or 'n/a'}",
        f"Category: {f.category}",
        f"Description: {f.description or 'n/a'}",
        f"Calories (per serving ref): {f.calories}",
        f"Carbohydrates g: {f.carbohydrates}, Fiber g: {f.fiber}, Protein g: {f.protein}, Fat g: {f.fat}",
        f"Glycemic index: {f.glycemic_index if f.glycemic_index is not None else 'unknown'}",
        f"Diabetes-friendly flag: {f.diabetes_friendly}",
    ]
    return "\n".join(parts)


def _embedding_fn():
    global _ef
    if _ef is None:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        _ef = SentenceTransformerEmbeddingFunction(model_name=config.RAG_EMBEDDING_MODEL)
    return _ef


def _persistent_client():
    global _client
    if _client is None:
        import chromadb

        config.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
    return _client


def _get_collection():
    """Always resolve collection from client (safe after rebuild deletes/recreates)."""
    client = _persistent_client()
    ef = _embedding_fn()
    try:
        return client.get_collection(name=config.RAG_COLLECTION, embedding_function=ef)
    except Exception:
        return client.create_collection(
            name=config.RAG_COLLECTION,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )


def rebuild_rag_index() -> int:
    """Rebuild Chroma collection from all FoodItem rows. Returns number of documents."""
    db = SessionLocal()
    try:
        foods = db.query(FoodItem).order_by(FoodItem.id).all()
        if not foods:
            logger.warning("RAG rebuild skipped: no foods in database")
            return 0
        client = _persistent_client()
        ef = _embedding_fn()
        try:
            client.delete_collection(config.RAG_COLLECTION)
        except Exception:
            pass
        coll = client.create_collection(
            name=config.RAG_COLLECTION,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        ids = [str(f.id) for f in foods]
        docs = [_food_document(f) for f in foods]
        coll.add(ids=ids, documents=docs)
        logger.info("RAG Chroma index rebuilt", extra={"documents": len(foods)})
        return len(foods)
    except Exception as e:
        logger.exception("RAG index rebuild failed: %s", e)
        raise
    finally:
        db.close()


def retrieve(query: str, k: int = 8) -> List[str]:
    """Return top-k document strings for the query (empty if index missing or error)."""
    pairs = retrieve_with_scores(query, k=k)
    return [d for d, _ in pairs]


def retrieve_with_scores(query: str, k: int = 8) -> List[tuple[str, float]]:
    """
    Top-k chunks with Chroma distance (cosine space: lower = closer match to the query embedding).
    """
    q = (query or "").strip()
    if not q:
        return []
    try:
        coll = _get_collection()
        n = coll.count()
        if n == 0:
            return []
        res = coll.query(query_texts=[q], n_results=min(k, max(1, n)))
        docs = res.get("documents") or [[]]
        dists = res.get("distances") or [[]]
        batch = docs[0] if docs else []
        drow = dists[0] if dists else []
        out: List[tuple[str, float]] = []
        for i, doc in enumerate(batch):
            if not doc:
                continue
            dist = float(drow[i]) if i < len(drow) and drow[i] is not None else 0.0
            out.append((doc, dist))
        return out
    except Exception as e:
        logger.warning("RAG retrieve failed: %s", e)
        return []
