"""
Embedding Pipeline - FAISS Index Builder
Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
"""

import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss
except ImportError:
    faiss = None

EMBEDDING_DIM = 384
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
INDEX_PATH = Path(os.getenv("FAISS_INDEX_PATH", "./data/faiss"))


def get_glycemic_category(gi: float) -> str:
    if gi is None or (isinstance(gi, float) and np.isnan(gi)):
        return "unknown"
    if gi <= 55:
        return "low"
    if gi <= 69:
        return "medium"
    return "high"


def build_food_embedding_text(food: Dict[str, Any]) -> str:
    """Build text representation for embedding."""
    parts = [
        food.get("name", ""),
        food.get("category", ""),
        f"calories: {food.get('calories', 0)}",
        f"protein: {food.get('protein', 0)}",
        f"carbs: {food.get('carbs', 0)}",
        f"glycemic index: {food.get('glycemic_index', 'unknown')}",
    ]
    tags = food.get("tags", [])
    if isinstance(tags, list):
        parts.extend(str(t) for t in tags)
    elif isinstance(tags, str):
        parts.append(tags)
    return " ".join(str(p) for p in parts)


def load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def generate_embeddings(texts: List[str], model: SentenceTransformer, batch_size: int = 32) -> np.ndarray:
    """Generate normalized embeddings for cosine similarity (IndexFlatIP)."""
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True)
    # L2 normalize for cosine similarity via inner product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    return embeddings.astype(np.float32)


def build_food_index(foods: List[Dict[str, Any]], output_dir: Path = INDEX_PATH) -> str:
    """Build FAISS index from food list. Returns path to index."""
    if faiss is None:
        raise ImportError("faiss-cpu required. pip install faiss-cpu")
    output_dir.mkdir(parents=True, exist_ok=True)
    model = load_model()
    texts = [build_food_embedding_text(f) for f in foods]
    embeddings = generate_embeddings(texts, model)
    metadata = []
    for f in foods:
        gi = f.get("glycemic_index")
        metadata.append({
            "food_id": str(f.get("id", "")),
            "category": f.get("category", ""),
            "glycemic_category": get_glycemic_category(gi) if gi is not None else "unknown",
            "tags": f.get("tags", []),
            "nutritional_summary": f"cal:{f.get('calories',0)} p:{f.get('protein',0)} c:{f.get('carbs',0)}",
        })
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)
    index_path = output_dir / "foods.index"
    meta_path = output_dir / "foods_metadata.pkl"
    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)
    return str(index_path)
