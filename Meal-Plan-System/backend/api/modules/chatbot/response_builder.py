"""Response builder - single responsibility: build reply from intent."""
import re
from typing import List


# Word-boundary / start-anchored only — substring "hi" must NOT match inside "which".
_GREETING_START = re.compile(
    r"^\s*(hello|hi|hey|hiya|yo|sup|hlo|hey\s+there|good\s+(morning|afternoon|evening))\b",
    re.IGNORECASE,
)
_GREETING_TOKENS = frozenset(
    {"hello", "hi", "hey", "hiya", "hlo", "yo", "sup", "howdy", "greetings"}
)

GI_WORDS = ["gi", "glycemic"]
CARB_WORDS = ["carb", "carbohydrate"]
# Steady-eating / prevention (not the same as "my sugar is high right now").
_STABILITY_PHRASES = (
    "keep my sugar",
    "sugar stable",
    "stable",
    "steady",
    "spike",
    "crash",
    "lower sugar",
    "control my",
    "good for diabetes",
    "normal level",
    "at normal",
    "stay in range",
    "in range",
)
# Phrases that imply glucose/sugar context without alone triggering stability food list.
_GLUCOSE_CONTEXT = (
    "blood sugar",
    "sugar level",
    "glucose",
    "bg ",
    "reading",
)
# Must not match definitional "which food is X" (leave that for search + single-food reply).
_GENERAL_FOOD_RE = re.compile(
    r"\b(what|which)\s+foods?\s+(can|should|could|would|to|for|that|help|keep|work|do|have)\b|"
    r"\b(what|which)\s+foods?\s+are\s+(good|best|okay|ok|safe|better|fine|low)\b|"
    r"\bfoods?\s+(with|that\s+have)\s+(low|the\s+lowest|less|minimal)\s+(sugar|carbs?)\b|"
    r"\b(low|lower|lowest)\s+(sugar|carb)\s+(foods?|content|choices?)\b|"
    r"\bwhich\s+.*\b(low|lower|lowest)\s+(sugar|carb)\b|"
    r"\bmeal\s+ideas?\b|\bsnack\s+ideas?\b|\beat\s+what\b",
    re.IGNORECASE,
)

# Short follow-ups that should stay in nutrition scope (handled in service when history exists).
_CONTINUATION_QUERY_RE = re.compile(
    r"(?ix)^\s*("
    r"give\s+me\s+more|"
    r"tell\s+me\s+more|"
    r"more\s+please|"
    r"can\s+you\s+(say|give)\s+more|"
    r"(go\s+on|continue|and\s+then)\s*\??|"
    r"(any\s+)?other\s+(examples?|tips?|ideas?)|"
    r"what\s+else|"
    r"expand(\s+on\s+that)?|"
    r"show\s+me\s+more"
    r")\s*[\?\!\.]*\s*$",
)


def is_nutrition_continuation_query(msg: str) -> bool:
    """Very short continuations like 'give me more' (use with non-empty chat history)."""
    raw = (msg or "").strip()
    if not raw or len(raw) > 72:
        return False
    if re.match(r"(?i)^\s*more\s*[\?\!\.]*\s*$", raw):
        return True
    return bool(_CONTINUATION_QUERY_RE.match(raw))


def is_low_sugar_foods_question(msg: str) -> bool:
    m = (msg or "").lower()
    if re.search(r"\b(low|lower|lowest|less|minimal)\s+(sugar|carb)", m):
        return True
    if re.search(r"\b(sugar|carb)\s+(content|amount)\b", m) and "which" in m:
        return True
    return False


def is_fruit_glucose_question(msg: str) -> bool:
    """Fruit + glucose balance (not a random single-food hit)."""
    m = (msg or "").lower()
    if not re.search(r"\bfruits?\b", m):
        return False
    fruit_q = re.search(
        r"\b(which|what|how)\s+.*\bfruits?\b|"
        r"\bfruits?\s+(for|with|and|or|in)\b|"
        r"\b(balance|balancing|stabil|steady|levels?|sugar\s+levels?|diabetes|portion|eat|include|choose|pick)\b",
        m,
    )
    return bool(fruit_q)
# Appended to rule-based replies when medically relevant (see service layer for exceptions).
DISCLAIMER = (
    "\n\n*This is general education, not personal medical advice—please work with your healthcare "
    "provider for guidance tailored to you.*"
)

# Strip these when loading chat history for the LLM (legacy + current wording).
DISCLAIMER_HISTORY_MARKERS = (
    "\n\nThis is general guidance",
    "\n\n*This is general education",
    "\n\n_This is general information only",
    "This is general guidance. Please consult your healthcare provider",
)


def strip_disclaimer_suffix(content: str) -> str:
    """Remove trailing disclaimer from persisted assistant text."""
    c = (content or "").strip()
    if not c:
        return c
    for marker in DISCLAIMER_HISTORY_MARKERS:
        if marker in c:
            return c.split(marker, 1)[0].strip()
    return c


def _reply_has_disclaimer(reply: str) -> bool:
    r = (reply or "").lower()
    return "healthcare" in r and ("general education" in r or "general guidance" in r or "medical advice" in r)


def append_disclaimer_if_needed(reply: str) -> str:
    """Append standard disclaimer unless already present (e.g. legacy saves)."""
    r = (reply or "").strip()
    if not r:
        return r
    if _reply_has_disclaimer(r):
        return r
    return r + DISCLAIMER


# Shared markdown body for "what can you do?" and off-topic guidance (frontend renders ** as bold).
_SCOPE_BODY_MARKDOWN = """**What I can help with**

- **Foods & meals** — Whether a food fits a diabetes-friendly pattern, **portion ideas**, and **lower-GI swaps** (for example matooke, beans, or rice).
- **Carbs & glycemic index (GI)** — How carbohydrates affect glucose and how to use GI as a practical guide.
- **Blood sugar context** — General education when you mention **high readings**, **low readings**, or **steady eating** (not personal insulin or medication doses).
- **Meal ideas** — Snacks and plates that combine fiber, protein, and smart carbohydrates.

**How to ask**

For example: *Is matooke good for diabetes?*, *What foods help keep blood sugar stable?*, or *What should I eat if my sugar is high?*

If your question is **not about nutrition or diabetes eating patterns**, I will gently steer you back to these topics."""

_SCOPE_INTENT_RE = re.compile(
    r"(?ix)^\s*("
    r"what\s+do\s+you\s+offer|"
    r"what\s+can\s+you\s+(do|help(\s+with)?|offer)|"
    r"what\s+('s|is)\s+(this|the)\s+(chat|bot|for)|"
    r"what\s+are\s+you\s+for|"
    r"how\s+(do|can)\s+i\s+use\s+(this|it)|"
    r"show\s+me\s+what\s+you\s+can\s+do|"
    r"what\s+should\s+i\s+ask|"
    r"what\s+.*\bscope\b|"
    r"what\s+.*\bcapabilities\b|"
    r"tell\s+me\s+about\s+(this|you)|"
    r"introduce\s+yourself"
    r")\s*[\?\!\.]*\s*$",
)
_SCOPE_HELP_ONLY_RE = re.compile(r"(?ix)^\s*help\s*[\?\!\.]*\s*$")


def is_scope_intent_query(msg: str) -> bool:
    """User explicitly asks what the assistant offers / how to use the chat."""
    raw = (msg or "").strip()
    if not raw or len(raw) > 160:
        return False
    if _SCOPE_HELP_ONLY_RE.match(raw):
        return True
    return bool(_SCOPE_INTENT_RE.match(raw))


def build_scope_welcome_reply() -> str:
    return (
        "Here is what this **Nutrition Assistant** can help you with.\n\n" + _SCOPE_BODY_MARKDOWN
    )


def build_off_topic_guidance_reply() -> str:
    """Same scope content as welcome; used when the topic classifier marks the message off-topic."""
    return (
        "That sounds **outside the nutrition topics** I am designed for. "
        "Here is what this chat **can** help you with:\n\n"
        + _SCOPE_BODY_MARKDOWN
    )


# Glucose numbers in user text (mg/dL assumed unless mmol/L is stated).
_GLUCOSE_CTX_RE = re.compile(
    r"blood\s+sugar|sugar\s+levels?|sugar\s+level|\bglucose\b|\bbg\b|"
    r"sugar.*\b(at|is|was|around|about|reading)|\b(at|is|was|around|about)\s+\d|"
    r"\b(what|how)\s+(about|of)\s+\d{2,3}\b|"
    r"\breadings?\s+(of|at|is|was)\s+\d{2,3}\b",
    re.IGNORECASE,
)
_MGDL_NUMS_RE = re.compile(r"\b(\d{2,3})\b")
_MMOL_RE = re.compile(r"\b(\d(?:\.\d+)?)\s*(?:mmol|mmol/l)\b", re.IGNORECASE)


def extract_glucose_readings_mgdl(msg: str) -> list[int]:
    """
    Pull plausible glucose values (mg/dL) when the sentence is clearly about readings.
    Ignores unrelated two-digit numbers when no glucose context.
    """
    raw = (msg or "").strip()
    if not raw:
        return []
    m = raw.lower()
    if not _GLUCOSE_CTX_RE.search(m):
        return []
    out: list[int] = []
    if "mmol" in m:
        for f in _MMOL_RE.findall(m):
            try:
                out.append(int(round(float(f) * 18)))
            except ValueError:
                continue
    for s in _MGDL_NUMS_RE.findall(m):
        n = int(s)
        if 50 <= n <= 350:
            out.append(n)
    # De-dupe preserving order
    seen = set()
    uniq: list[int] = []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def classify_numeric_glucose_scenario(readings: list[int]) -> str | None:
    """
    Map readings to reply template key. Thresholds are educational defaults (mg/dL).
    """
    if not readings:
        return None
    lo, hi = min(readings), max(readings)
    if lo < 80:
        return "treating_low"
    if hi >= 250:
        return "high_number"
    if hi >= 180:
        return "elevated_number"
    return "near_target_meal"


def build_glucose_numeric_reply(scenario: str, readings: list[int], foods: List[dict]) -> str:
    """Distinct guidance for numeric BG + food questions (legacy path)."""
    lo, hi = min(readings), max(readings)
    rtxt = ", ".join(str(x) for x in readings)

    if scenario == "treating_low":
        disclaimer = (
            f"You mentioned **{rtxt} mg/dL** (assuming **mg/dL** on your meter — confirm units with your clinician). "
        )
        if lo < 54:
            intro = (
                disclaimer
                + "A reading **this low** is **serious** for many people — **treat as hypoglycemia** right away per your care plan.\n\n"
            )
        elif lo < 70:
            intro = (
                disclaimer
                + f"**{lo} mg/dL** is **below the rough ~70 mg/dL lower-alert level** many teams use — usually treated as a **low** (hypoglycemia), though **your own thresholds may differ**.\n\n"
            )
        else:
            intro = (
                disclaimer
                + "**Around 70 mg/dL** is often used as a **lower-alert level** by many teams, and your reading is **in that borderline zone** — **your personal target may differ**.\n\n"
            )
        base = (
            intro
            + "**First:** follow your **low treatment plan** — many use about **15 g fast-acting carbohydrate** "
            "(e.g. juice, glucose tablets, or regular soda), wait ~**15 minutes**, **recheck**, and repeat if still low. "
            "Use **glucagon** or emergency help if needed.\n\n"
            "**Food after you're back in range:** choose a **small balanced snack or meal** with **protein and fiber**, "
            "not only sweets, unless your team says otherwise. Avoid stacking heavy carbs until you've confirmed you're safe."
        )
    elif scenario == "high_number":
        base = (
            f"A reading around **{rtxt} mg/dL** is **high** for most people. **Do not rely on food alone** to fix it — "
            "use the **correction plan** from your clinician (insulin/meds, fluids, when to call).\n\n"
            "For **what to eat next**, once your team says it's appropriate: favor **lower-GI, fiber-rich** choices and "
            "**measured portions** of carbohydrate; skip extra sugary drinks."
        )
    elif scenario == "elevated_number":
        base = (
            f"**{rtxt} mg/dL** is on the **higher** side for many adults. Pair any food advice with your **care plan** "
            "for corrections and recheck timing.\n\n"
            "For **meal building** at elevated readings: emphasize **non-starchy vegetables**, **lean protein**, and "
            "**moderate** lower-GI carbs; avoid grazing on extra sweets until you're back toward your usual target range."
        )
    else:  # near_target_meal — e.g. 120
        base = (
            f"**{rtxt} mg/dL** can be **reasonable for some people** depending on **when** you measured (fasting vs after a meal) "
            f"and **your own targets** — only your clinician can say what's right for you.\n\n"
            "If you're simply **planning what to eat** at a level like this, aim for **balanced meals**: plenty of "
            "**non-starchy vegetables**, **lean protein**, and a **modest** serving of **lower-GI carbs** with fiber "
            "(beans, lentils, oats, whole grains). **Portion size** still matters more than one snapshot number."
        )

    if foods and scenario in ("near_target_meal", "elevated_number", "high_number"):
        bits = []
        for f in foods[:5]:
            gi = f.get("glycemic_index")
            gi_s = str(gi) if gi is not None else "n/a"
            bits.append(f"{f['name']} (GI {gi_s}, {f.get('fiber', 0)}g fiber)")
        return f"{base}\n\nExamples from this app's food list: {'; '.join(bits)}."
    if foods and scenario == "treating_low":
        # Lighter examples: still useful but not identical to long GI lecture
        names = ", ".join(f["name"] for f in foods[:4])
        return f"{base}\n\nAfter treating the low, **fiber-forward options** from our list can work for a follow-up meal: {names}."

    return base


def is_greeting(msg: str) -> bool:
    s = (msg or "").strip()
    if not s:
        return False
    if _GREETING_START.match(s):
        return True
    tokens = re.findall(r"[a-z']+", s.lower())
    if len(s) <= 18 and len(tokens) <= 3 and tokens and all(t in _GREETING_TOKENS for t in tokens):
        return True
    return False


def is_gi_question(msg: str) -> bool:
    return any(w in msg.lower() for w in GI_WORDS)


def is_carb_question(msg: str) -> bool:
    return any(w in msg.lower() for w in CARB_WORDS)


def is_high_bg_question(msg: str) -> bool:
    """User is worried about high readings / hyperglycemia — not the same as 'foods for stable sugar'."""
    m = (msg or "").lower()
    if "hyperglycem" in m:
        return True
    if "what if" in m and "high" in m and any(
        x in m for x in ("sugar", "glucose", "reading", "level", "number")
    ):
        return True
    has_plain_high = bool(
        re.search(r"\b(too\s+)?high\b|\bvery\s+high\b|\belevated\b", m)
    )
    has_spike = bool(re.search(r"\bspike[ds]?\b|\bwent\s+up\b", m))
    if not has_plain_high and not has_spike:
        return False
    if has_spike and not any(
        x in m for x in ("sugar", "glucose", "reading", "blood sugar", " bg", "bg ", "level", "number")
    ):
        return False
    if re.search(r"\bhigh\s+(gi|glycemic|fiber|protein)\b", m):
        return False
    if any(x in m for x in _GLUCOSE_CONTEXT):
        return True
    if re.search(r"\b(my|the)\s+.*\b(sugar|glucose)\b", m):
        return True
    return False


def is_low_bg_question(msg: str) -> bool:
    m = (msg or "").lower()
    if "hypoglycem" in m or re.search(r"\bhypo\b", m):
        return True
    if re.search(r"\b(shaky|dizzy|sweating)\b", m) and any(
        x in m for x in ("sugar", "glucose", "low", "reading")
    ):
        return True
    if not re.search(r"\b(too\s+)?low\b", m):
        return False
    if re.search(r"\blow\s+(gi|glycemic|carb)\b", m):
        return False
    if any(x in m for x in _GLUCOSE_CONTEXT):
        return True
    if re.search(r"\b(my|the)\s+.*\b(sugar|glucose)\b", m):
        return True
    return False


def is_stability_question(msg: str) -> bool:
    m = (msg or "").lower()
    if is_high_bg_question(msg) or is_low_bg_question(msg):
        return False
    # Numeric BG + food → handled by glucose reading templates, not generic stability blurb.
    if extract_glucose_readings_mgdl(msg) and re.search(
        r"\b(eat|food|meal|snack|diet|supposed|should|kind)\b", m
    ):
        return False
    if any(p in m for p in _STABILITY_PHRASES):
        return True
    # "glucose/sugar level" alone: only stability if about eating/prevention, not highs/lows (handled above).
    if any(c in m for c in _GLUCOSE_CONTEXT) and not re.search(
        r"\b(high|low|elevated|hypo|hyper)\b", m
    ):
        if re.search(
            r"\b(eat|food|meal|snack|diet|which|what|kind|carb|gi|glycemic)\b",
            m,
        ):
            return True
    return False


def is_general_food_question(msg: str) -> bool:
    """Broad 'what/which foods…' without requiring the word 'stable'."""
    return bool(_GENERAL_FOOD_RE.search(msg or ""))


def build_greeting_reply() -> str:
    return (
        "Hello. I am your **Nutrition Assistant** for diabetes-friendly eating. "
        "You can ask about specific foods, carbohydrates, glycemic index, meal ideas, or what to consider when readings run high or low. "
        "For example: *Is matooke a good choice for diabetes?*"
    )


def build_gi_reply() -> str:
    return (
        "**Glycemic index (GI)** describes how quickly a carbohydrate food tends to raise blood glucose after eating. "
        "Foods with a **low GI (about 55 or less)** usually raise glucose more gently than high-GI choices. "
        "Many people with diabetes emphasize beans, lentils, non-starchy vegetables, and whole grains, and they use **portion size** and **what you pair with carbs** (protein, fiber, healthy fats) to keep responses steadier."
    )


def build_carb_reply() -> str:
    return (
        "**Carbohydrates** have the largest effect on blood glucose for most people. "
        "**Fiber** slows digestion and can soften rises; **protein** and **non-starchy vegetables** help make meals more filling without piling on extra fast carbs. "
        "A practical approach is to choose **mostly lower-GI carbs**, watch **portions**, and build plates that balance carb quality with fiber and protein."
    )


def build_high_bg_reply() -> str:
    return (
        "If your **reading is high**, the priority is to follow the **plan your clinician gave you** for corrections "
        "(insulin, medication timing, when to call the clinic, and how often to recheck). This app cannot adjust doses for you.\n\n"
        "Many care teams also teach general steps such as: **hydrate with water**, avoid adding **extra carbohydrates** until you know your plan, "
        "and **recheck** as directed. If you feel very unwell, are vomiting, see large ketones (if you test), or your glucose stays "
        "very high, **seek urgent care** according to your team's instructions.\n\n"
        "For **food after you have addressed the high** with your care plan: the next meal is a good time for **lower-GI, "
        "fiber-rich choices** and careful **portion sizes**—similar to everyday steady-glucose eating, **not** as a substitute for medical steps."
    )


def build_low_bg_reply() -> str:
    return (
        "If you think your **blood sugar is low**, follow what your clinician taught you — often **15 g fast-acting carbohydrate**, "
        "wait ~15 minutes, **recheck**, and repeat if still low. Use glucagon or emergency help if you cannot swallow or symptoms are severe.\n\n"
        "This assistant cannot tell you your personal thresholds or doses. If lows are frequent, discuss pattern changes with your care team.\n\n"
        "After treating a low, many people choose a **small balanced snack** with some protein if the next meal is not soon — "
        "your team can suggest what fits your plan."
    )


def _food_examples_sentence(foods: List[dict], limit: int = 5) -> str:
    bits = []
    for f in foods[:limit]:
        gi = f.get("glycemic_index")
        gi_s = str(gi) if gi is not None else "n/a"
        bits.append(f"**{f['name']}** (GI {gi_s}, {f.get('fiber', 0)} g fiber)")
    return "; ".join(bits)


def build_stability_reply(foods: List[dict]) -> str:
    base = (
        "To help keep blood glucose **steadier**, many people emphasize foods with a **lower glycemic index (often around ≤55)**, **more fiber**, and **enough protein**—and they pay attention to **portion size** and **what they pair with carbohydrates**. "
        "Common patterns include **non-starchy vegetables**, **beans and lentils**, **steel-cut or rolled oats**, **unsweetened yogurt**, **small portions of nuts**, and **whole grains** instead of refined flour when grains are on the plate."
    )
    if foods:
        return f"{base}\n\n**Examples** from this app's food list: {_food_examples_sentence(foods)}."
    return base


def build_nutrition_continuation_reply(foods: List[dict]) -> str:
    """Rule-based follow-up when the user asks for 'more' and no LLM reply is available."""
    intro = (
        "Here is **more you can use in day-to-day eating**: aim for **regular meals** that combine "
        "**lean protein**, **high-fiber foods**, and **lower-GI carbohydrates** in portions that match what your care team recommends. "
        "Spreading carbohydrate across the day, choosing **whole or minimally processed** options when you can, and **limiting sugary drinks** all support steadier glucose for many people."
    )
    if foods:
        return f"{intro}\n\n**Examples** from this app's food list: {_food_examples_sentence(foods)}."
    return intro


def build_fruit_glucose_reply(foods: List[dict]) -> str:
    body = (
        "You **can** include **fruit** in a diabetes-friendly pattern; the keys are **how much**, **how often**, and **what you pair it with**. "
        "**Whole fruit** (with fiber) often affects glucose more gently than **juice** or **dried fruit** in large amounts. "
        "Many clinicians suggest watching **total carbohydrate** at the meal or snack, not only the word “sugar” on the label. "
        "Berries, apples, and citrus are often discussed as **portion-friendly** options; **tropical fruits** can still fit if you adjust **portion size** and balance the rest of the plate."
    )
    if foods:
        return f"{body}\n\n**Examples** from this database (use portions your team approves): {_food_examples_sentence(foods)}."
    return body


def build_low_sugar_foods_reply(foods: List[dict]) -> str:
    intro = (
        "When people ask for **“low sugar”** foods, it helps to think about **added sugars**, **total carbohydrate**, and **glycemic index** together. "
        "**Non-starchy vegetables**, **legumes**, and many **whole grains** are often good building blocks because they bring **fiber** and tend to have a **moderate or low GI**. "
        "If you are comparing packaged items, check **grams of carbohydrate** and **added sugar** per serving, not marketing words alone."
    )
    if foods:
        return f"{intro}\n\n**Examples** from this app's list (numbers are illustrative—confirm portions with your clinician): {_food_examples_sentence(foods)}."
    return intro


def build_food_reply(food: dict) -> str:
    gi = food.get("glycemic_index") or "N/A"
    df = (
        "It is often considered **diabetes-friendly in appropriate portions**."
        if food.get("diabetes_friendly")
        else "**Enjoy in smaller portions** or less often, depending on your overall plan."
    )
    return (
        f"**{food['name']}** — about **{food['calories']} kcal** per serving in this database, "
        f"**glycemic index {gi}**, **{food.get('carbohydrates', 0)} g carbohydrate**, **{food.get('fiber', 0)} g fiber**. {df}"
    )


def build_fallback_reply(foods: List[dict] | None = None) -> str:
    if foods:
        return build_stability_reply(foods)
    return (
        "I can help with **specific foods** (for example matooke or beans), **glycemic index**, **carbohydrates**, or **meal ideas** for steadier glucose. "
        "Try naming a food, or ask something like: *What foods help keep blood sugar stable?*"
    )
