"""Database-backed meal and food-list helpers for the nutrition chatbot."""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from api.models import FoodItem
from api.modules.chatbot.response_builder import (
    classify_numeric_glucose_scenario,
    extract_glucose_readings_mgdl,
    is_high_bg_question,
    is_low_bg_question,
)

_MEAL_DATASET = Path(__file__).resolve().parents[3] / "datasets" / "diabetic_diet_meal_plans_with_macros_GI.csv"

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_CATEGORY_ALIASES = {
    "fruit": "fruits",
    "fruits": "fruits",
    "vegetable": "vegetables",
    "vegetables": "vegetables",
    "veggie": "vegetables",
    "veggies": "vegetables",
    "greens": "vegetables",
    "bean": "legumes",
    "beans": "legumes",
    "legume": "legumes",
    "legumes": "legumes",
    "lentil": "legumes",
    "lentils": "legumes",
    "cowpea": "legumes",
    "cowpeas": "legumes",
    "soybean": "legumes",
    "soybeans": "legumes",
    "groundnut": "legumes",
    "groundnuts": "legumes",
    "grain": "grains",
    "grains": "grains",
    "bread": "grains",
    "rice": "grains",
    "fish": "fish",
    "protein": "protein",
    "egg": "protein",
    "eggs": "protein",
    "meat": "protein",
    "chicken": "protein",
    "staple": "staple",
    "staples": "staple",
    "tuber": "tubers",
    "tubers": "tubers",
}

_MEAL_TYPE_PATTERNS = (
    (re.compile(r"\bbreakfast\b", re.IGNORECASE), "breakfast"),
    (re.compile(r"\blunch\b", re.IGNORECASE), "lunch"),
    (re.compile(r"\b(dinner|supper)\b", re.IGNORECASE), "dinner"),
    (re.compile(r"\bsnack\b", re.IGNORECASE), "snack"),
)

_FULL_DAY_RE = re.compile(
    r"\b(full\s*day|whole\s*day|all\s*day|for\s*the\s*day|in\s*a\s*day|today'?s?\s+meals?|daily\s+meal\s+plan|meal\s+plan)\b",
    re.IGNORECASE,
)

_LIST_RE = re.compile(
    r"\b(list|show|give|state|name|tell)\b.*\bfoods?\b|"
    r"\b(what|which)\s+foods?\s+(are|for|can|should)\b|"
    r"\bdiabet(?:es|ic)[-\s]*friendly\s+foods?\b",
    re.IGNORECASE,
)

_LOCAL_RE = re.compile(r"\b(local|uganda|ugandan|traditional|home\s*foods?)\b", re.IGNORECASE)


def _parse_float(raw: str | None) -> float:
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


@lru_cache(maxsize=1)
def load_meal_templates() -> list[dict]:
    """Load unique diabetic meal-combination rows from the CSV dataset."""
    if not _MEAL_DATASET.exists():
        return []

    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    with _MEAL_DATASET.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            group = (row.get("Group") or "").strip().lower()
            if not group.startswith("diabetic"):
                continue
            meal_type = (row.get("Meal") or "").strip().lower()
            preference = (row.get("Veg/Non-Veg") or "").strip().lower()
            dish = (row.get("Dish") or "").strip()
            if not meal_type or not dish:
                continue
            key = (meal_type, preference, dish.lower())
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "meal_type": meal_type,
                    "preference": preference,
                    "dish": dish,
                    "calories": _parse_float(row.get("Calories")),
                    "protein": _parse_float(row.get("Protein")),
                    "carbs": _parse_float(row.get("Carbs")),
                    "fat": _parse_float(row.get("Fat")),
                    "fiber": _parse_float(row.get("Fiber")),
                    "glycemic_index": int(_parse_float(row.get("Glycemic Index")) or 0),
                }
            )
    return rows


def detect_meal_type(message: str) -> str | None:
    raw = (message or "").strip()
    if not raw:
        return None
    if _FULL_DAY_RE.search(raw):
        return "full_day"
    for pattern, meal_type in _MEAL_TYPE_PATTERNS:
        if pattern.search(raw):
            return meal_type
    return None


def requested_count(message: str, *, default: int, minimum: int = 1, maximum: int = 8) -> int:
    raw = (message or "").lower()
    m = re.search(r"\b(\d{1,2})\b", raw)
    if m:
        return max(minimum, min(maximum, int(m.group(1))))
    for word, value in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", raw):
            return max(minimum, min(maximum, value))
    return default


def detect_preference(message: str) -> str | None:
    raw = (message or "").lower()
    if re.search(r"\b(vegetarian|vegan|veg)\b", raw):
        return "veg"
    if re.search(r"\b(non[-\s]?veg|meat|fish|chicken|egg)\b", raw):
        return "non-veg"
    return None


def prefer_local_foods(message: str) -> bool:
    return bool(_LOCAL_RE.search(message or ""))


def detect_glucose_context(message: str) -> str | None:
    raw = (message or "").strip()
    if not raw:
        return None
    readings = extract_glucose_readings_mgdl(raw)
    if readings and (scenario := classify_numeric_glucose_scenario(readings)):
        return scenario
    if is_low_bg_question(raw):
        return "treating_low"
    if is_high_bg_question(raw):
        return "high_number"
    return None


def is_food_list_request(message: str) -> bool:
    raw = (message or "").strip().lower()
    if not raw:
        return False
    if detect_meal_type(raw):
        return False
    if _LIST_RE.search(raw):
        return True
    return bool(requested_count(raw, default=0) and re.search(r"\bfoods?\b", raw))


def detect_requested_categories(message: str) -> list[str]:
    raw = (message or "").lower()
    found: list[str] = []
    for alias, category in _CATEGORY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", raw) and category not in found:
            found.append(category)
    return found


def _food_is_non_veg(food: FoodItem) -> bool:
    category = (food.category or "").lower()
    name = (food.name or "").lower()
    return category in {"fish"} or any(token in name for token in ("chicken", "fish", "tilapia", "silver fish"))


def _food_matches_preference(food: FoodItem, preference: str | None) -> bool:
    if not preference:
        return True
    if preference == "veg":
        return not _food_is_non_veg(food)
    if preference == "non-veg":
        return _food_is_non_veg(food) or (food.category or "").lower() == "protein"
    return True


def _food_rank(
    food: FoodItem,
    *,
    preference: str | None = None,
    local_first: bool = False,
    glucose_context: str | None = None,
) -> tuple:
    gi = food.glycemic_index if food.glycemic_index is not None else 999
    local_rank = 0 if (local_first and (food.local_name or "").strip()) else 1
    pref_rank = 0 if _food_matches_preference(food, preference) else 1
    carbs = float(food.carbohydrates or 0)
    fiber = float(food.fiber or 0)
    protein = float(food.protein or 0)
    if glucose_context in {"high_number", "elevated_number"}:
        return (pref_rank, local_rank, gi, carbs, -fiber, -protein, (food.name or "").lower())
    if glucose_context == "treating_low":
        moderate_carb_gap = abs(carbs - 18.0)
        return (pref_rank, local_rank, moderate_carb_gap, -protein, -fiber, gi, (food.name or "").lower())
    return (pref_rank, local_rank, gi, -fiber, -protein, carbs, (food.name or "").lower())


def load_food_candidates(
    db: Session,
    *,
    limit: int,
    categories: list[str] | None = None,
    preference: str | None = None,
    local_first: bool = False,
    glucose_context: str | None = None,
) -> list[FoodItem]:
    q = db.query(FoodItem).filter(FoodItem.diabetes_friendly.is_(True))
    if categories:
        q = q.filter(FoodItem.category.in_(categories))
    rows = q.all()
    if preference == "veg":
        rows = [row for row in rows if _food_matches_preference(row, preference)]
    rows.sort(
        key=lambda row: _food_rank(
            row,
            preference=preference,
            local_first=local_first,
            glucose_context=glucose_context,
        )
    )
    return rows[:limit]


def build_food_list_reply(db: Session, message: str) -> str | None:
    count = requested_count(message, default=5, maximum=10)
    categories = detect_requested_categories(message)
    preference = detect_preference(message)
    local_first = prefer_local_foods(message)
    glucose_context = detect_glucose_context(message)
    foods = load_food_candidates(
        db,
        limit=max(count, 8),
        categories=categories or None,
        preference=preference,
        local_first=local_first,
        glucose_context=glucose_context,
    )
    if not foods:
        return None

    shown = foods[:count]
    scope = "foods"
    if categories:
        scope = ", ".join(categories)
    if preference == "veg":
        scope = f"vegetarian-friendly {scope}"
    elif preference == "non-veg":
        scope = f"non-veg-friendly {scope}"
    if local_first:
        scope = f"local Ugandan {scope}"

    if glucose_context == "treating_low":
        intro = (
            f"If your sugar is low, treat the low first using your care plan. "
            f"After you are back in range, here are {len(shown)} {scope} options from the app database:"
        )
    elif glucose_context in {"high_number", "elevated_number"}:
        intro = (
            f"Since you mentioned a high reading, follow your correction plan first. "
            f"For steadier eating afterward, here are {len(shown)} {scope} options from the app database:"
        )
    else:
        intro = f"Here are {len(shown)} diabetes-friendly {scope} options from the app database:"

    lines = [intro]
    for idx, food in enumerate(shown, start=1):
        gi = food.glycemic_index if food.glycemic_index is not None else "n/a"
        local_note = f"; local name: {food.local_name}" if (food.local_name or "").strip() else ""
        lines.append(
            f"{idx}. {food.name} ({food.category}{local_note}; GI {gi}; {food.carbohydrates:.1f}g carbs; {food.fiber:.1f}g fiber)"
        )
    lines.append("If you want, I can also group these into breakfast, lunch, dinner, or snack ideas.")
    return "\n".join(lines)


def _sort_templates(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            int(row.get("glycemic_index") or 999),
            float(row.get("carbs") or 0),
            -float(row.get("protein") or 0),
            (row.get("dish") or "").lower(),
        ),
    )


def _select_templates(message: str, meal_type: str, default_count: int) -> list[dict]:
    templates = load_meal_templates()
    pref = detect_preference(message)
    rows = [row for row in templates if row["meal_type"] == meal_type]
    if pref:
        preferred = [row for row in rows if row["preference"] == pref]
        if preferred:
            rows = preferred
    rows = _sort_templates(rows)
    return rows[: requested_count(message, default=default_count, maximum=5)]


def _pick_best_food(
    db: Session,
    categories: list[str],
    excluded: set[str],
    *,
    preference: str | None = None,
    local_first: bool = False,
    glucose_context: str | None = None,
) -> FoodItem | None:
    rows = load_food_candidates(
        db,
        limit=25,
        categories=categories,
        preference=preference,
        local_first=local_first,
        glucose_context=glucose_context,
    )
    for row in rows:
        if row.name not in excluded:
            return row
    return None


def _build_fallback_meal_combo(db: Session, meal_type: str) -> str | None:
    return _build_personalized_fallback_meal_combo(db, meal_type, None, False, None)


def _build_personalized_fallback_meal_combo(
    db: Session,
    meal_type: str,
    preference: str | None,
    local_first: bool,
    glucose_context: str | None,
) -> str | None:
    excluded: set[str] = set()
    if glucose_context == "treating_low":
        if meal_type == "breakfast":
            category_sets = (["fruits", "grains", "staple"], ["protein", "legumes"])
        elif meal_type == "snack":
            category_sets = (["fruits", "grains"], ["protein", "legumes"])
        else:
            category_sets = (["grains", "staple", "tubers"], ["protein", "legumes", "protein_dishes"], ["vegetables"])
    elif glucose_context in {"high_number", "elevated_number"}:
        if meal_type == "breakfast":
            category_sets = (["legumes", "protein", "protein_dishes"], ["fruits"], ["vegetables"])
        elif meal_type == "lunch":
            category_sets = (["protein", "fish", "legumes", "protein_dishes"], ["vegetables"], ["grains", "staple"])
        elif meal_type == "dinner":
            category_sets = (["protein", "fish", "legumes", "protein_dishes"], ["vegetables"], ["grains", "staple"])
        else:
            category_sets = (["protein", "legumes"], ["fruits"], [])
    else:
        if meal_type == "breakfast":
            category_sets = (["grains", "staple", "tubers"], ["protein", "legumes"], ["fruits"])
        elif meal_type == "lunch":
            category_sets = (["grains", "staple", "tubers"], ["protein", "fish", "legumes", "protein_dishes"], ["vegetables"])
        elif meal_type == "dinner":
            category_sets = (["protein", "fish", "legumes", "protein_dishes"], ["vegetables"], ["grains", "staple", "tubers"])
        else:
            category_sets = (["fruits"], ["protein", "legumes"], [])

    parts: list[str] = []
    for categories in category_sets:
        if not categories:
            continue
        food = _pick_best_food(
            db,
            categories,
            excluded,
            preference=preference,
            local_first=local_first,
            glucose_context=glucose_context,
        )
        if not food:
            continue
        excluded.add(food.name)
        parts.append(food.name)
    if not parts:
        return None
    return " + ".join(parts)


def _meal_context_note(meal_type: str, glucose_context: str | None) -> str:
    if glucose_context == "treating_low":
        return (
            f"If you are currently low, treat the low first using your care plan. "
            f"Once you are back in range, these {meal_type} ideas can work as balanced follow-up food."
        )
    if glucose_context in {"high_number", "elevated_number"}:
        return (
            f"If your reading is high, follow your care plan first. "
            f"For the next {meal_type}, these ideas keep carbs more measured and pair them with protein and fiber."
        )
    return ""


def build_meal_reply(db: Session, message: str, meal_type: str) -> str | None:
    preference = detect_preference(message)
    local_first = prefer_local_foods(message)
    glucose_context = detect_glucose_context(message)
    if meal_type == "full_day":
        plan: list[str] = []
        for single in ("breakfast", "lunch", "snack", "dinner"):
            chosen = _select_templates(message, single, default_count=1)
            if chosen:
                row = chosen[0]
                plan.append(
                    f"- {single.title()}: {row['dish']} (GI {row['glycemic_index']}, {row['carbs']:.1f}g carbs, {row['protein']:.1f}g protein)"
                )
            else:
                combo = _build_personalized_fallback_meal_combo(
                    db,
                    single,
                    preference,
                    local_first,
                    glucose_context,
                )
                if combo:
                    plan.append(f"- {single.title()}: {combo}")
        if not plan:
            return None
        intro = "Here is a diabetes-friendly day of meal ideas based on the app data:"
        if preference == "veg":
            intro = "Here is a vegetarian diabetes-friendly day of meal ideas based on the app data:"
        elif preference == "non-veg":
            intro = "Here is a non-veg-friendly diabetes meal day based on the app data:"
        if local_first:
            intro = intro.replace("Here is", "Here is a local Ugandan-style")
        context_note = _meal_context_note("meals", glucose_context)
        if context_note:
            intro = f"{context_note}\n\n{intro}"
        return intro + "\n" + "\n".join(plan)

    chosen = _select_templates(message, meal_type, default_count=3)
    if chosen:
        descriptor = f"diabetes-friendly {meal_type}"
        if preference == "veg":
            descriptor = f"vegetarian {descriptor}"
        elif preference == "non-veg":
            descriptor = f"non-veg-friendly {descriptor}"
        if local_first:
            descriptor = f"local Ugandan-style {descriptor}"
        lines = []
        context_note = _meal_context_note(meal_type, glucose_context)
        if context_note:
            lines.append(context_note)
            lines.append("")
        lines.append(f"Here are {len(chosen)} {descriptor} ideas from the app meal dataset:")
        for idx, row in enumerate(chosen, start=1):
            lines.append(
                f"{idx}. {row['dish']} (GI {row['glycemic_index']}, {row['carbs']:.1f}g carbs, {row['protein']:.1f}g protein, {row['fiber']:.1f}g fiber)"
            )
        lines.append("Aim for a balanced plate: controlled carbs, a protein source, and fiber-rich vegetables or fruit where appropriate.")
        return "\n".join(lines)

    combo = _build_personalized_fallback_meal_combo(
        db,
        meal_type,
        preference,
        local_first,
        glucose_context,
    )
    if combo:
        descriptor = f"diabetes-friendly {meal_type}"
        if preference == "veg":
            descriptor = f"vegetarian {descriptor}"
        elif preference == "non-veg":
            descriptor = f"non-veg-friendly {descriptor}"
        if local_first:
            descriptor = f"local Ugandan-style {descriptor}"
        context_note = _meal_context_note(meal_type, glucose_context)
        body = (
            f"A {descriptor} idea from the app food database is: {combo}.\n"
            "Try to keep the carb portion measured and pair it with protein plus fiber for steadier glucose."
        )
        return f"{context_note}\n\n{body}" if context_note else body
    return None

