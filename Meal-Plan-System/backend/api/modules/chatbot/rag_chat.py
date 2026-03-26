"""
RAG + LLM answer generation for the nutrition chatbot.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from api.core import config
from api.modules.chatbot import llm_client
from api.modules.chatbot.rag_store import retrieve_with_scores
from api.modules.search.service import search_foods

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a careful nutrition assistant for people managing diabetes (including Type 1 and Type 2).

Rules:
- Use the **recent conversation** when the user asks a follow-up (e.g. "what if…", "and then?", "what about lows?"). Answer **that** question; do not repeat your previous answer unless they ask you to.
- Ground answers about **specific foods** in the RETRIEVED CONTEXT below when it is relevant. Prefer facts from context over general memory.
- If the context does not mention the user's food, say so briefly and give **general** diabetes-friendly guidance (portion awareness, carbs, fiber, GI concepts) without inventing numbers for that food.
- For **high or low blood sugar episodes**, give **education only**: encourage following their care plan, when to seek urgent care in broad terms, and sensible nutrition context — never prescribe insulin/medication doses or replace emergency advice.
- Keep answers concise (about 3–8 short sentences). Use plain language.
- Do **not** diagnose disease, change medications, or give personal medical orders. Encourage seeing a clinician for medical decisions.
- Do **not** repeat or add a legal disclaimer at the end (the application adds one automatically).

RETRIEVED CONTEXT (from app food database; may be incomplete):
---
{context}
---
"""


def _clinical_prompt_supplement() -> str:
    p = Path(config.CLINICAL_PROMPT_SUPPLEMENT_PATH)
    if not p.is_file():
        return ""
    try:
        text = p.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    cap = int(config.CLINICAL_PROMPT_SUPPLEMENT_MAX_CHARS)
    return (text[:cap] if text else "").strip()


def build_system_message(context: str) -> str:
    body = SYSTEM_PROMPT.format(context=context)
    extra = _clinical_prompt_supplement()
    if extra:
        body += (
            "\n\n---\nADDITIONAL GUIDANCE (from project clinical prompt document; "
            "still not a substitute for a clinician):\n"
            + extra
        )
    return body


def _food_search_chunks(db: Session, message: str, limit: int = 5) -> List[str]:
    foods = search_foods(db, message, limit=limit, diabetes_only=True)
    out = []
    for f in foods:
        gi = f.get("glycemic_index")
        out.append(
            f"Food: {f.get('name')} (local: {f.get('local_name') or 'n/a'}), "
            f"category {f.get('category')}, {f.get('calories')} kcal, "
            f"GI {gi if gi is not None else 'unknown'}, "
            f"carbs {f.get('carbohydrates')}g, fiber {f.get('fiber')}g, "
            f"diabetes_friendly={f.get('diabetes_friendly')}."
        )
    return out


def _snippet(doc: str, max_len: int = 100) -> str:
    line = (doc or "").split("\n")[0].strip()
    if len(line) > max_len:
        return line[: max_len - 1] + "…"
    return line


def format_retrieval_explanation(meta: list[dict]) -> str:
    lines = []
    for m in meta[:10]:
        src = m.get("source", "")
        sn = m.get("snippet", "")
        dist = m.get("distance")
        if src == "vector" and dist is not None:
            lines.append(
                f"• **Chroma vector match**: {sn} _(embedding distance **{dist:.3f}**; lower = closer to your question)_."
            )
        elif src == "food_search":
            lines.append(f"• **Food search (SQL/Typesense)**: {sn}")
        else:
            lines.append(f"• {sn}")
    return "\n".join(lines) if lines else "• (No retrieval metadata.)"


def build_context_and_meta(
    db: Session, user_message: str, vector_k: int = 8
) -> tuple[str, list[dict], str]:
    """
    Returns (context_string, retrieval_meta, retrieval_explanation_text).
    """
    scored = retrieve_with_scores(user_message, k=vector_k)
    chunks: List[str] = [d for d, _ in scored]
    meta: list[dict] = [
        {"source": "vector", "snippet": _snippet(d), "distance": dist}
        for d, dist in scored
    ]
    seen = set(chunks)
    for line in _food_search_chunks(db, user_message, limit=5):
        if line not in seen:
            chunks.append(line)
            seen.add(line)
            meta.append({"source": "food_search", "snippet": _snippet(line, 120), "distance": None})
    if not chunks:
        empty = "(No matching passages were retrieved from the food database for this question.)"
        return empty, [], "• No vector or search hits were returned for this query."
    ctx = "\n\n---\n\n".join(chunks)
    return ctx, meta, format_retrieval_explanation(meta)


def build_context(db: Session, user_message: str, vector_k: int = 8) -> str:
    ctx, _, _ = build_context_and_meta(db, user_message, vector_k=vector_k)
    return ctx


def generate_rag_reply(
    db: Session,
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> tuple[str | None, str]:
    """
    Returns (assistant_text_or_none, retrieval_explanation_markdown).
    """
    if not llm_client.is_llm_configured():
        return None, ""
    context, _meta, retr_txt = build_context_and_meta(db, user_message)
    messages: list[dict] = [
        {"role": "system", "content": build_system_message(context)},
    ]
    for turn in conversation_history or []:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        messages.append({"role": role, "content": content[:6000]})
    messages.append({"role": "user", "content": user_message})
    text = llm_client.chat(messages)
    if not text:
        return None, retr_txt
    return text, retr_txt
