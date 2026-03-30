"""Chatbot service - RAG + LLM when configured; else rule-based replies."""
from sqlalchemy.orm import Session

from api.core import config
from api.models import ChatMessage
from api.modules.search.service import search_foods
from api.modules.chatbot import llm_client, rag_chat, topic_nlp
from api.modules.chatbot.response_builder import (
    is_greeting,
    is_gi_question,
    is_carb_question,
    is_high_bg_question,
    is_low_bg_question,
    is_stability_question,
    is_general_food_question,
    is_nutrition_continuation_query,
    is_fruit_glucose_question,
    is_low_sugar_foods_question,
    extract_glucose_readings_mgdl,
    classify_numeric_glucose_scenario,
    build_glucose_numeric_reply,
    build_greeting_reply,
    build_gi_reply,
    build_carb_reply,
    build_high_bg_reply,
    build_low_bg_reply,
    build_stability_reply,
    build_food_reply,
    build_fallback_reply,
    build_nutrition_continuation_reply,
    build_fruit_glucose_reply,
    build_low_sugar_foods_reply,
    append_disclaimer_if_needed,
    strip_disclaimer_suffix,
    is_scope_intent_query,
    build_scope_welcome_reply,
    build_off_topic_guidance_reply,
)
from api.core.logging_config import get_logger

logger = get_logger("api.chatbot.service")

_FALLBACK_SEARCH_TERMS = (
    "vegetables",
    "beans",
    "lentils",
    "oats",
    "matooke",
)


def load_prior_history(db: Session, user_id: int, session_id: int) -> list[dict]:
    """Messages in this session before the current send, for LLM context (disclaimer stripped)."""
    limit = config.CHATBOT_HISTORY_MAX
    if limit <= 0:
        return []
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == user_id,
            ChatMessage.chat_session_id == session_id,
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    out: list[dict] = []
    for r in rows:
        role = r.role if r.role in ("user", "assistant") else "user"
        content = (r.content or "").strip()
        if role == "assistant":
            content = strip_disclaimer_suffix(content)
        if content:
            out.append({"role": role, "content": content})
    return out


def retrieve_foods(db: Session, message: str, user_id: int = 0) -> list:
    """Retrieve relevant foods from search (rule-based path)."""
    foods = search_foods(db, message, limit=5, diabetes_only=True)
    if not foods and len((message or "").strip()) > 20:
        n = len(_FALLBACK_SEARCH_TERMS)
        start = user_id % n if n else 0
        rotated = list(range(start, n)) + list(range(0, start))
        for i in rotated:
            term = _FALLBACK_SEARCH_TERMS[i]
            foods = search_foods(db, term, limit=5, diabetes_only=True)
            if foods:
                break
    if not foods:
        return []
    return [{
        "name": f["name"],
        "calories": f["calories"],
        "glycemic_index": f.get("glycemic_index"),
        "carbohydrates": f["carbohydrates"],
        "fiber": f["fiber"],
        "diabetes_friendly": f["diabetes_friendly"],
    } for f in foods]


def save_message(db: Session, user_id: int, role: str, content: str, session_id: int) -> None:
    """Persist chat message and bump session activity."""
    from api.modules.chatbot import session_service

    try:
        db.add(
            ChatMessage(
                user_id=user_id,
                role=role,
                content=content,
                chat_session_id=session_id,
            )
        )
        db.commit()
        session_service.touch_session(db, session_id)
    except Exception as e:
        logger.error("Failed to save message", extra={"error": str(e)})
        db.rollback()


def generate_reply(db: Session, user_id: int, message: str, session_id: int) -> str:
    """Generate chatbot reply: LLM+RAG if configured, else keyword rules."""
    from api.modules.chatbot import session_service

    if not session_service.get_owned_session(db, user_id, session_id):
        raise ValueError("Invalid or unknown chat session")

    msg = (message or "").strip()
    if not msg:
        return "Please ask a question about nutrition, foods, or diabetes management."

    prior = load_prior_history(db, user_id, session_id)
    save_message(db, user_id, "user", message, session_id)
    session_service.maybe_set_title_from_first_message(db, session_id, message)

    if is_scope_intent_query(msg):
        reply = build_scope_welcome_reply()
        save_message(db, user_id, "assistant", reply, session_id)
        return reply

    skip_topic = is_greeting(msg) or (bool(prior) and is_nutrition_continuation_query(msg))
    topic_analysis = None
    if not skip_topic and config.CHATBOT_TOPIC_NLP_ENABLED:
        topic_analysis = topic_nlp.analyze_message(msg)
        if topic_analysis.get("ok") and not topic_analysis.get("on_topic"):
            body = build_off_topic_guidance_reply()
            save_message(db, user_id, "assistant", body, session_id)
            return body

    # Explicit mg/dL-style numbers (e.g. 70 vs 120): deterministic, distinct guidance.
    # Runs before LLM so answers stay consistent even when an API key is set.
    readings = extract_glucose_readings_mgdl(msg)
    if readings and (scenario := classify_numeric_glucose_scenario(readings)):
        foods_num = retrieve_foods(db, msg, user_id)
        reply = build_glucose_numeric_reply(scenario, readings, foods_num)
        full = append_disclaimer_if_needed(reply)
        save_message(db, user_id, "assistant", full, session_id)
        return full

    use_llm = (
        not config.CHATBOT_USE_LEGACY_ONLY
        and llm_client.is_llm_configured()
    )

    if use_llm:
        try:
            reply, _ = rag_chat.generate_rag_reply(db, msg, conversation_history=prior)
            if reply:
                save_message(db, user_id, "assistant", reply, session_id)
                return reply
        except Exception as e:
            logger.warning("RAG+LLM chat failed, using rule-based fallback", extra={"error": str(e)})

    foods = retrieve_foods(db, msg, user_id=user_id)

    if is_nutrition_continuation_query(msg) and prior:
        alt = retrieve_foods(db, "vegetables beans oats yogurt berries lentils", user_id=user_id)
        if alt:
            foods = alt
        reply = build_nutrition_continuation_reply(foods)
    elif is_greeting(msg):
        reply = build_greeting_reply()
    elif is_high_bg_question(msg):
        reply = build_high_bg_reply()
    elif is_low_bg_question(msg):
        reply = build_low_bg_reply()
    elif is_fruit_glucose_question(msg):
        reply = build_fruit_glucose_reply(foods)
    elif is_low_sugar_foods_question(msg):
        reply = build_low_sugar_foods_reply(foods)
    elif is_gi_question(msg):
        reply = build_gi_reply()
    elif is_carb_question(msg):
        reply = build_carb_reply()
    elif is_stability_question(msg) or is_general_food_question(msg):
        reply = build_stability_reply(foods)
    elif foods:
        reply = build_food_reply(foods[0])
    else:
        reply = build_fallback_reply(foods)

    if not is_greeting(msg):
        reply = append_disclaimer_if_needed(reply)
    save_message(db, user_id, "assistant", reply, session_id)
    return reply
