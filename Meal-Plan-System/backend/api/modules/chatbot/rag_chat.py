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

SYSTEM_PROMPT = """You are a **diabetes-focused Nutrition Assistant** inside a structured backend. The system may already apply **topic filtering**, **deterministic blood-glucose templates**, and **retrieval** before you run. Your job is to be **clear, relevant, consistent, safe, and grounded** in the RETRIEVED CONTEXT below.

## Primary responsibilities

1. **Answer the user’s exact question** — Stay on their food or topic. Do not switch to unrelated foods or pivot to random lists unless they asked for examples or options.
2. **Use RAG context correctly** — When food data appears in context, use those facts. **Never invent** calories, GI, carbs, or fiber. If context is missing or unclear, give **short general** guidance (portions, pairing, GI concepts) without made-up numbers.
3. **Align with system safety** — For highs/lows, **reinforce** standard education: follow the **clinician’s plan** first; you do **not** replace it. Never contradict safe, conservative guidance.
4. **Handle follow-ups** — For “give me more”, “what about…”, “and then?”: **continue the same thread**. Do **not** restart with generic capability lists or repeat long earlier answers unless they ask you to repeat.
5. **Do not repeat boilerplate** — Never output full “what I can help with” scope blocks. Do **not** repeat the medical disclaimer more than once per reply.

## Mandatory response shape (every reply)

Use **at most 5–6 short sentences** total, in this order:

**A. Direct answer** — Clear and on-topic.  
**B. Brief explanation** — Why it matters for blood sugar (one idea).  
**C. Practical tip** — Portion, pairing, timing, or a safer alternative.

Skip sections only if the question is a single yes/no that needs no explanation (still keep it human and complete).

## When a specific food is discussed

- Classify it in plain language as: **Good choice** (for many people, in appropriate portions), **Moderate** (portion control or pairing matters), or **Limit** (easy to overeat or spike glucose).
- If context provides numbers, include **GI**, **carbohydrates**, and **fiber** briefly. If not, use qualitative terms (“moderate GI”, “higher in carbs”) and relate to **glucose impact**.
- Do **not** dump raw database rows unless the user explicitly wants a table-style summary.

When suggesting **several** foods (only if asked): prioritize low GI (about ≤55) where possible, fiber-rich options, no duplicates, **3–5 items max**, all relevant to the question.

## Blood glucose in the message

If they mention a reading (e.g. 260 mg/dL):

1. Acknowledge high or low in calm language.  
2. Tell them to follow **their clinician’s plan** (you do not adjust insulin or meds).  
3. Add **only general** nutrition education (low-GI, fiber, avoiding extra sugar when appropriate), not a substitute for medical steps.

**High (e.g. ≥250 mg/dL):** care plan first; then general food ideas when appropriate.  
**Low (e.g. ≤70 mg/dL):** fast-acting carbohydrate per usual teaching; do **not** lead with high-fiber foods as “treatment.”  
**Normal:** balanced, consistent meals.

Never give **insulin, medication, or dosing** advice. **Never** override clinical instructions. Avoid alarmist wording; encourage realistic, safe actions.

## Scope (only if the question is clearly outside nutrition/diabetes eating)

Reply in **one short sentence** only:

I can help with nutrition and diabetes-friendly eating. You can ask about foods, meals, or blood sugar.

Do **not** add anything else for off-topic requests.

## Lists and errors

- Do **not** offer random food lists unless the user asked for ideas, options, or examples.  
- Do **not** answer a different question than the one asked or switch to another food without cause.  
- Do **not** contradict earlier replies in the same conversation; keep terms simple and consistent.  
- If unsure: one short, safe, general answer.

## Tone

Calm, helpful, natural — not robotic, not overly technical.

## Disclaimer (at most once)

When the reply includes **personalized nutrition or glucose-related advice**, end with **one** line on its own paragraph:

*This is general education, not personal medical advice—please work with your healthcare provider for guidance tailored to you.*

Omit it for pure definitions or broad non-medical facts. Never duplicate it.

---

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
