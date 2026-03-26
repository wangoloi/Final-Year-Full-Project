"""
RAG Pipeline for Diabetes Chatbot
- Document chunking
- Embedding generation
- Retrieval ranking
- Safety filter (no insulin dosage advice)
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50

# Safety: block responses that could be dangerous
FORBIDDEN_PATTERNS = [
    r"\d+\s*units?\s*(of\s*)?insulin",
    r"inject\s*\d+",
    r"take\s*\d+\s*units",
    r"insulin\s*dosage",
    r"adjust\s*your\s*insulin",
]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Simple sentence-aware chunking."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = []
    current_len = 0
    for s in sentences:
        if current_len + len(s) > chunk_size and current:
            chunks.append(" ".join(current))
            overlap_sentences = []
            overlap_len = 0
            for x in reversed(current):
                if overlap_len + len(x) <= overlap:
                    overlap_sentences.insert(0, x)
                    overlap_len += len(x)
                else:
                    break
            current = overlap_sentences
            current_len = overlap_len
        current.append(s)
        current_len += len(s)
    if current:
        chunks.append(" ".join(current))
    return chunks


def safety_filter(text: str) -> bool:
    """Return False if text contains forbidden patterns (e.g. insulin dosage advice)."""
    lower = text.lower()
    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return False
    return True


def enrich_response(response: str, context: Optional[Dict] = None) -> str:
    """Add disclaimers and context to chatbot response."""
    disclaimer = "\n\n_This is general information only. Always consult your healthcare provider for medical advice._"
    if not safety_filter(response):
        return "I cannot provide specific insulin dosage or medication advice. Please consult your doctor or diabetes care team."
    return response + disclaimer


class RAGPipeline:
    """
    Complete RAG pipeline: embed -> retrieve -> build context -> generate response.
    Uses nutrition knowledge base when available; falls back to rule-based responses.
    """

    def __init__(self, embedding_model=None, vector_store=None):
        self._embedding = embedding_model
        self._store = vector_store
        self._model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self._model = SentenceTransformer(MODEL_NAME)
            except Exception:
                pass

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant chunks from vector store."""
        if not self._store or self._store.count() == 0:
            return []
        try:
            if self._model:
                q_emb = self._model.encode(query)
            elif self._embedding:
                q_emb = self._embedding.embed_query(query)
            else:
                return []
            ids, metas, _ = self._store.query(q_emb, n_results=top_k)
            return [{"id": i, "metadata": m or {}, "content": (m or {}).get("content", "")} for i, m in zip(ids, metas)]
        except Exception:
            return []

    def build_context(self, retrieved: List[Dict], max_chars: int = 1500) -> str:
        """Build context string from retrieved chunks."""
        parts = []
        total = 0
        for r in retrieved:
            content = r.get("content") or r.get("metadata", {}).get("content", "")
            if content and total + len(content) <= max_chars:
                parts.append(content)
                total += len(content)
        return "\n\n".join(parts) if parts else ""

    def generate(self, query: str, context: str) -> str:
        """Generate response from query and context. Rule-based for diabetes nutrition."""
        q = (query or "").strip().lower()
        if not q:
            return "Please ask a question about nutrition, foods, or diabetes management."

        # Rule-based generation using context and query
        if any(w in q for w in ["hello", "hi", "hey"]):
            return (
                "Hi! I'm your nutrition assistant for diabetes management. "
                "Ask me about foods, blood sugar, meal ideas, or alternatives. "
                "For example: 'Is matooke good for diabetes?' or 'What foods keep blood sugar stable?'"
            )
        if any(w in q for w in ["gi", "glycemic", "glycemic index"]):
            return (
                "Glycemic Index (GI) measures how fast a food raises blood sugar. "
                "Low (≤55) is best for diabetes. Medium (56-69): moderate. High (≥70): fast spike. "
                "Prefer beans, lentils, vegetables, and whole grains. Limit white rice and refined flour."
            )
        if any(w in q for w in ["carb", "carbohydrate"]):
            return (
                "Carbohydrates have the biggest impact on blood sugar. Fiber slows their absorption. "
                "Choose whole grains, legumes, and vegetables. Pair carbs with protein."
            )
        if any(w in q for w in ["stable", "stability", "control", "good for diabetes"]):
            return (
                "Foods with low GI (≤55), high fiber, and moderate protein help keep blood sugar stable. "
                "Good choices: beans, lentils, oats, vegetables, whole grains. "
                "Use Search or Recommendations for personalized suggestions."
            )
        if any(w in q for w in ["breakfast", "lunch", "dinner", "meal"]):
            return (
                "A balanced meal for diabetes includes whole grains, protein, and fiber. "
                "Combine: (1) Complex carbs like oatmeal or millet, "
                "(2) Protein like eggs, beans, or yogurt, "
                "(3) Fiber from vegetables or fruit. This slows glucose absorption."
            )
        if context:
            return (
                f"Based on our nutrition knowledge:\n\n{context[:800]}...\n\n"
                "For specific foods, use the Search feature. For diabetes, prefer low GI (≤55) and high fiber."
            )
        return (
            "I'm your nutrition assistant for diabetes. "
            "Try: 'Is matooke good for diabetes?', 'What's a good breakfast?', "
            "or 'Which foods keep blood sugar stable?'"
        )

    def run(self, query: str, top_k: int = 5) -> str:
        """Full pipeline: retrieve -> build context -> generate -> enrich."""
        retrieved = self.retrieve(query, top_k=top_k)
        context = self.build_context(retrieved)
        response = self.generate(query, context)
        return enrich_response(response)
