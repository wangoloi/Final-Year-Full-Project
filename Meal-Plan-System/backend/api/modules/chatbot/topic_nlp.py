"""
Transformer embeddings (sentence-transformers) + sklearn logistic regression with
**exact linear SHAP values** for the topic classifier (Lundberg–Lee: additive model).

Each feature is cosine similarity to an anchor *theme* (mean of reference sentences).
SHAP φⱼ = wⱼ·(xⱼ − 𝔼[Xⱼ]) with independent features; they sum to the deviation of the logit
from its baseline at the background distribution. This explains **why** the classifier
judged a message on- or off-topic — not token-level SHAP inside a generative LLM.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from api.core import config

logger = logging.getLogger(__name__)

_pipeline: dict[str, Any] | None = None
_pipeline_error: str | None = None

# Anchor themes: each list is averaged into one direction in embedding space.
ANCHOR_GROUPS: dict[str, list[str]] = {
    "Diabetes & meal planning": [
        "managing type 1 and type 2 diabetes with diet and insulin awareness",
        "healthy meals and snacks for people with diabetes",
        "carb counting and portion sizes for blood sugar control",
    ],
    "Foods, carbs & glycemic index": [
        "glycemic index and carbohydrate content of foods",
        "rice matooke beans vegetables and whole grains for glucose",
        "low sugar high fiber foods and diabetes friendly choices",
    ],
    "Glucose readings & highs or lows": [
        "blood sugar readings hyperglycemia hypoglycemia and glucose targets",
        "what to do when sugar is high or low besides medication",
        "steady glucose and avoiding spikes with food choices",
    ],
    "General nutrition coaching": [
        "balanced diet protein fiber hydration and mindful eating",
        "weight and energy in the context of chronic disease nutrition",
    ],
    "Off-topic: technology & coding": [
        "python javascript programming software bugs and algorithms",
        "installing apps servers databases and writing code",
    ],
    "Off-topic: unrelated daily chat": [
        "sports scores weather movies celebrity gossip travel booking",
        "homework algebra history unrelated to health or food",
    ],
}

POS_TRAIN = [
    "give me more examples",
    "tell me more about that",
    "more please",
    "is matooke good for diabetes",
    "which foods keep blood sugar stable",
    "what carbs can I eat with type 2",
    "glycemic index of sweet potato",
    "meal ideas for low gi dinner",
    "is posho bad for glucose",
    "how much rice for a diabetic portion",
    "snacks that won't spike insulin",
    "beans lentils and blood sugar",
    "fruit and diabetes how much",
    "what if my sugar level is high",
    "hypoglycemia snack ideas after treating low",
    "fiber and post meal glucose",
    "oatmeal versus cornflakes for diabetes",
    "ugandan foods for diabetic diet",
    "insulin and counting carbohydrates at lunch",
    "water and high blood sugar education",
    "vegetables with lowest impact on glucose",
    "nuts and diabetes portions",
    "yogurt unsweetened and blood sugar",
    "whole grain bread gi value",
    "plantain fried diabetes friendly or not",
    "cassava and glucose response",
    "millet porridge for diabetics",
    "egg and avocado breakfast sugar impact",
    "dinner without refined flour",
    "reading nutrition labels for sugar",
    "alternatives to soda for diabetics",
    "protein pairing with carbohydrates",
]

NEG_TRAIN = [
    "write a python function to sort a list",
    "how do I fix npm install error",
    "who won the premier league yesterday",
    "translate this paragraph to japanese",
    "capital of australia trivia",
    "best gaming laptop under 1000",
    "schedule a haircut appointment email template",
    "explain quantum computing for beginners",
    "stock price prediction lstm keras",
    "docker compose kubernetes tutorial",
    "funny joke about programmers",
    "movie review spoiler ending",
    "weather forecast next week paris",
    "how to unlock my iphone without password",
    "sql injection example exploit",
    "cryptocurrency mining profitability",
    "car engine oil change steps",
    "flight tickets cheap london to nairobi",
    "dating app opening lines",
    "philosophy of consciousness debate",
    "repair leaky kitchen faucet",
    "minecraft redstone clock",
    "excel formula vlookup example",
    "powerpoint slide transition effects",
    "who is the president of france",
    "nearest pizza delivery open now",
    "guitar chord progression pop song",
    "zodiac sign compatibility horoscope",
    "refund policy amazon order dispute",
]


def _cosine_features(
    text_emb: np.ndarray,
    group_centroids: np.ndarray,
) -> np.ndarray:
    """text_emb: (d,), group_centroids: (n_groups, d) normalized."""
    return np.dot(group_centroids, text_emb)


def _build_pipeline() -> dict[str, Any]:
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression

    model_name = config.RAG_EMBEDDING_MODEL
    logger.info("Loading sentence-transformers model for topic NLP: %s", model_name)
    st = SentenceTransformer(model_name)

    names = list(ANCHOR_GROUPS.keys())
    centroids = []
    for sentences in ANCHOR_GROUPS.values():
        emb = st.encode(sentences, normalize_embeddings=True, show_progress_bar=False)
        c = np.mean(emb, axis=0)
        n = np.linalg.norm(c)
        centroids.append(c / n if n > 1e-9 else c)
    group_centroids = np.stack(centroids, axis=0)

    def featurize_one(t: str) -> np.ndarray:
        e = st.encode([t], normalize_embeddings=True, show_progress_bar=False)[0]
        return _cosine_features(e, group_centroids)

    X_pos = np.stack([featurize_one(t) for t in POS_TRAIN], axis=0)
    X_neg = np.stack([featurize_one(t) for t in NEG_TRAIN], axis=0)
    X = np.vstack([X_pos, X_neg])
    y = np.array([1] * len(POS_TRAIN) + [0] * len(NEG_TRAIN))

    clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    clf.fit(X, y)

    bg_size = min(80, X.shape[0])
    rng = np.random.RandomState(42)
    idx = rng.choice(X.shape[0], size=bg_size, replace=False)
    X_bg = X[idx]

    return {
        "st": st,
        "clf": clf,
        "feature_names": names,
        "centroids": group_centroids,
        "featurize_one": featurize_one,
        "X_background": X_bg,
    }


def get_pipeline() -> dict[str, Any] | None:
    global _pipeline, _pipeline_error
    if not config.CHATBOT_TOPIC_NLP_ENABLED:
        return None
    if _pipeline_error:
        return None
    if _pipeline is not None:
        return _pipeline
    try:
        _pipeline = _build_pipeline()
    except Exception as e:
        _pipeline_error = str(e)
        logger.warning("Topic NLP pipeline unavailable: %s", e)
        return None
    return _pipeline


def _linear_shap_values(
    clf,
    x: np.ndarray,
    X_bg: np.ndarray,
) -> tuple[np.ndarray, float, float]:
    """
    Exact SHAP for logistic regression under independent features (additive on logit).
    Returns (phi per feature, baseline logit E[logit], model logit at x).
    """
    x = x.ravel()
    mu = X_bg.mean(axis=0)
    w = clf.coef_.ravel()
    b = float(clf.intercept_[0])
    phi = w * (x - mu)
    baseline_logit = float(w @ mu + b)
    logit_x = float(w @ x + b)
    return phi, baseline_logit, logit_x


def _format_shap_explanation(
    feature_names: list[str],
    phi: np.ndarray,
    baseline_logit: float,
    logit_x: float,
) -> str:
    pairs = list(zip(feature_names, phi))
    pairs.sort(key=lambda t: -abs(t[1]))
    lines = []
    for name, val in pairs[:6]:
        direction = "supports nutrition scope" if val >= 0 else "pulls toward off-topic"
        lines.append(f"• **{name}**: SHAP **{val:+.3f}** ({direction}).")
    lines.append(
        f"• _Baseline logit_ (expected at training mix): **{baseline_logit:+.3f}**; "
        f"_logit for your message_: **{logit_x:+.3f}** (mapped to on-topic probability after sigmoid)._"
    )
    return "\n".join(lines)


def analyze_message(text: str) -> dict[str, Any]:
    """
    Returns keys: on_topic (bool), proba_on_topic (float), shap_text (str),
    feature_vector (list[float] optional), ok (bool), error (str optional).
    """
    q = (text or "").strip()
    if not q:
        return {
            "ok": True,
            "on_topic": False,
            "proba_on_topic": 0.0,
            "shap_text": "",
            "error": None,
        }

    pipe = get_pipeline()
    if pipe is None:
        return {
            "ok": False,
            "on_topic": True,
            "proba_on_topic": 1.0,
            "shap_text": "",
            "error": _pipeline_error,
        }

    clf = pipe["clf"]
    names = pipe["feature_names"]
    featurize_one = pipe["featurize_one"]
    X_bg = pipe["X_background"]

    x = featurize_one(q).reshape(1, -1)
    proba = clf.predict_proba(x)[0]
    p_on = float(proba[1])
    max_anchor_sim = float(np.max(x))

    threshold = config.CHATBOT_TOPIC_THRESHOLD
    # Soft gate: model score OR strong raw similarity to any positive anchor cluster (first 4 groups).
    strong_theme = max_anchor_sim >= config.CHATBOT_TOPIC_MAXSIM_FALLBACK
    on_topic = (p_on >= threshold) or strong_theme

    try:
        phi, base_logit, logit_x = _linear_shap_values(clf, x, X_bg)
        shap_text = _format_shap_explanation(names, phi, base_logit, logit_x)
    except Exception as e:
        logger.warning("SHAP explanation failed: %s", e)
        shap_text = (
            "• (SHAP-style attribution unavailable; topic score still used.)\n"
            f"• Model **P(on-topic)** ≈ **{p_on:.2f}**; strongest anchor cosine ≈ **{max_anchor_sim:.2f}**."
        )

    return {
        "ok": True,
        "on_topic": on_topic,
        "proba_on_topic": p_on,
        "max_anchor_sim": max_anchor_sim,
        "shap_text": shap_text,
        "error": None,
    }


def off_topic_reply(_shap_text: str) -> str:
    """User-facing only — no internal SHAP / classifier dump in the chat bubble."""
    from api.modules.chatbot.response_builder import build_off_topic_guidance_reply

    return build_off_topic_guidance_reply()
