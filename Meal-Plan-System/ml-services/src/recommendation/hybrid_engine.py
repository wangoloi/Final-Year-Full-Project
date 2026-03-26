"""
Hybrid Recommendation Engine
- Rule-based safety filtering
- Content-based (cosine similarity)
- Collaborative filtering (SVD)
- ML ranking (Gradient Boosting)
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import joblib

# Optional imports
try:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.ensemble import GradientBoostingClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

DIABETES_GI_LIMITS = {"type_1": 55, "type_2": 55, "gestational": 55, "prediabetes": 60}
MODEL_PATH = Path(os.getenv("RECOMMENDATION_MODEL_PATH", "./data/models/ranking_model.joblib"))


class HybridRecommendationEngine:
    def __init__(self):
        self.ranking_model = None
        if MODEL_PATH.exists() and SKLEARN_AVAILABLE:
            self.ranking_model = joblib.load(MODEL_PATH)

    def rule_based_filter(
        self,
        foods: List[Dict],
        diabetes_type: Optional[str] = None,
        allergies: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Safety filtering by diabetes type and allergies."""
        filtered = []
        max_gi = DIABETES_GI_LIMITS.get(diabetes_type, 70) if diabetes_type else 70
        allergy_set = set((a or "").lower() for a in (allergies or []))
        for f in foods:
            gi = f.get("glycemic_index")
            if gi is not None and gi > max_gi:
                continue
            tags = f.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            tag_str = " ".join(str(t).lower() for t in tags)
            if any(a in tag_str for a in allergy_set if a):
                continue
            filtered.append(f)
        return filtered

    def content_based_rank(
        self,
        candidate_embeddings: np.ndarray,
        user_preference_embedding: Optional[np.ndarray] = None,
        k: int = 10,
    ) -> np.ndarray:
        """Rank by cosine similarity to user preference. Returns indices."""
        if user_preference_embedding is None:
            return np.arange(min(k, len(candidate_embeddings)))
        scores = np.dot(candidate_embeddings, user_preference_embedding)
        return np.argsort(scores)[::-1][:k]

    def diversity_injection(self, ranked_indices: np.ndarray, diversity_factor: float = 0.3) -> np.ndarray:
        """Simple diversity: interleave with random picks."""
        n = len(ranked_indices)
        if n <= 1:
            return ranked_indices
        num_random = max(1, int(n * diversity_factor))
        rng = np.random.default_rng()
        random_picks = rng.choice(n, size=min(num_random, n), replace=False)
        combined = np.concatenate([ranked_indices[: n - num_random], random_picks])
        return np.unique(combined, return_inverse=True)[0]

    def ml_rank(
        self,
        features: np.ndarray,
        top_k: int = 10,
    ) -> np.ndarray:
        """Rank using trained Gradient Boosting model."""
        if self.ranking_model is None or not SKLEARN_AVAILABLE:
            return np.arange(min(top_k, len(features)))
        probs = self.ranking_model.predict_proba(features)[:, 1]
        return np.argsort(probs)[::-1][:top_k]

    def recommend(
        self,
        foods: List[Dict],
        user_profile: Optional[Dict] = None,
        candidate_embeddings: Optional[np.ndarray] = None,
        user_embedding: Optional[np.ndarray] = None,
        k: int = 10,
    ) -> List[Dict]:
        """Full pipeline: filter -> content rank -> diversity -> return."""
        user_profile = user_profile or {}
        filtered = self.rule_based_filter(
            foods,
            diabetes_type=user_profile.get("diabetes_type"),
            allergies=user_profile.get("allergies"),
        )
        if not filtered:
            return []
        if candidate_embeddings is not None and user_embedding is not None:
            indices = self.content_based_rank(candidate_embeddings, user_embedding, k=k * 2)
            indices = self.diversity_injection(indices)
            result = [filtered[i] for i in indices[:k] if i < len(filtered)]
        else:
            result = filtered[:k]
        return result
