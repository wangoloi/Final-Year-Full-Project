"""
User-centered meal guidance: compose foods into meals, immediate next action, avoid lists.
Educational only — not medical advice.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from api.models import FoodItem

from api.modules.recommendations.engine.context_model import GlucoseStateModel
from api.modules.recommendations.engine.optimization import ScoredCandidate


def _user_facing_glucose_level(gsm: GlucoseStateModel) -> str:
    if gsm.state == "unknown_no_data":
        return "unknown"
    if gsm.state in ("critical_high", "rising_high", "elevated"):
        return "high"
    if gsm.state == "falling_low":
        return "low"
    return "normal"


def _macro_role(f: FoodItem) -> str:
    """Coarse role for meal assembly (protein / fiber / fat / carb / general)."""
    p = float(f.protein or 0)
    carbs = float(f.carbohydrates or 0)
    fiber = float(f.fiber or 0)
    fat = float(f.fat or 0)
    cat = (f.category or "").lower()
    name = (f.name or "").lower()

    if p >= 10 and carbs < 38:
        return "protein"
    if fiber >= 4 or "vegetable" in cat or "greens" in name or "salad" in name:
        return "fiber"
    if fat >= 10 and carbs < 35 and fiber < 6:
        return "fat"
    if carbs >= 35:
        return "carb"
    if p >= 6:
        return "protein"
    return "general"


def _food_label(f: FoodItem) -> str:
    return f.name if not f.local_name else f"{f.name} ({f.local_name})"


def _compose_meal_from_buckets(
    buckets: Dict[str, List[FoodItem]],
    gsm: GlucoseStateModel,
) -> Tuple[List[FoodItem], str]:
    """
    Pick 2–3 foods into a composed meal; returns (foods, meal_type_label).
    Mutates bucket copies — work on deep copies for multiple meals.
    """
    # Work on shallow copies of lists
    b = {k: list(v) for k, v in buckets.items()}

    def take(role: str) -> Optional[FoodItem]:
        if b.get(role):
            return b[role].pop(0)
        return None

    foods: List[FoodItem] = []
    if gsm.state in ("critical_high", "rising_high", "elevated"):
        meal_type = "light stabilizing meal"
        for role in ("protein", "fiber", "fat"):
            f = take(role)
            if f:
                foods.append(f)
        if len(foods) < 2:
            for role in ("protein", "general", "fiber"):
                f = take(role)
                if f and f not in foods:
                    foods.append(f)
                if len(foods) >= 3:
                    break
    elif gsm.state == "falling_low":
        meal_type = "quick-balance meal"
        for role in ("carb", "protein", "fiber"):
            f = take(role)
            if f:
                foods.append(f)
        if len(foods) < 2:
            for role in ("general", "protein"):
                f = take(role)
                if f and f not in foods:
                    foods.append(f)
                if len(foods) >= 2:
                    break
    else:
        meal_type = "balanced plate"
        for role in ("protein", "fiber", "general"):
            f = take(role)
            if f:
                foods.append(f)
        if len(foods) < 2:
            for role in ("carb", "fat"):
                f = take(role)
                if f and f not in foods:
                    foods.append(f)
                if len(foods) >= 2:
                    break

    # Fallback: first available
    if len(foods) < 2:
        for role in list(b.keys()):
            while b.get(role) and len(foods) < 3:
                f = take(role)
                if f and f not in foods:
                    foods.append(f)
            if len(foods) >= 2:
                break

    return foods[:3], meal_type


def _meal_title(foods: List[FoodItem]) -> str:
    if not foods:
        return "Balanced choices from your list"
    parts = [_food_label(f) for f in foods]
    return " + ".join(parts)


def _highlights(gsm: GlucoseStateModel) -> List[str]:
    if gsm.state in ("critical_high", "rising_high", "elevated"):
        return ["Low sugar impact", "High fiber", "Keeps you full"]
    if gsm.state == "falling_low":
        return ["Structured carbs", "Protein to follow up", "Steady energy"]
    return ["Balanced nutrients", "Fiber-forward", "Sensible portions"]


def _reason_next_meal(gsm: GlucoseStateModel) -> str:
    if gsm.state in ("critical_high", "rising_high", "elevated"):
        return "Low in quick carbs, rich in fiber and protein—helps blunt spikes and stabilize glucose."
    if gsm.state == "falling_low":
        return "Pairs structured carbohydrate with protein so your level can recover steadily—follow your hypo plan from your clinician."
    if gsm.state == "unknown_no_data":
        return "A balanced, diabetes-smart plate while we learn your readings—log glucose for tailored picks."
    return "Balanced protein, fiber, and smart carbs to keep meals steady."


def _when_to_eat(hour: int, gsm: GlucoseStateModel) -> str:
    if gsm.state in ("critical_high", "rising_high", "elevated"):
        return "Within the next hour, or at your next planned meal."
    if gsm.state == "falling_low":
        return "Soon—if you have symptoms of low sugar, follow your clinician’s fast-carb steps first."
    if 5 <= hour < 11:
        return "Breakfast or your next morning snack."
    if 11 <= hour < 15:
        return "Lunchtime."
    if 15 <= hour < 19:
        return "Afternoon snack or early dinner."
    return "Dinner or your usual evening meal."


def _avoid_list(level: str, gsm: GlucoseStateModel) -> List[str]:
    base = [
        "Very large portions of white rice, posho, or bread in one sitting",
        "Sugary drinks, juice, and regular soda",
        "Sweets and pastries as the main fuel for a meal",
    ]
    if level == "high" or gsm.state in ("critical_high", "rising_high", "elevated"):
        return base + ["Extra honey/sugar on top of already carb-heavy plates"]
    if level == "low":
        return [
            "Drinking alcohol on an empty stomach",
            "Skipping the next meal after treating a low without your care team’s plan",
        ]
    return base[:2] + ["Skipping vegetables and protein when carbs are high"]


def _narrative_explanation(gsm: GlucoseStateModel, text_ctx: Dict[str, str], meal_title: str) -> str:
    trend_note = ""
    if gsm.trend == "increasing":
        trend_note = " Your recent readings suggest an upward trend, so lighter carbs and more fiber help slow absorption."
    elif gsm.trend == "decreasing":
        trend_note = " Your trend looks softer—still keep meals balanced unless your team advises otherwise."

    if gsm.state in ("critical_high", "rising_high", "elevated"):
        return (
            f"Your glucose has been elevated. A plate like “{meal_title}” emphasizes protein and fiber with fewer fast carbs, "
            f"which can help steady sugar after meals.{trend_note} This is educational guidance—not a substitute for your care plan."
        )
    if gsm.state == "falling_low":
        return (
            f"Your readings look on the low side. “{meal_title}” combines structured carbohydrate with protein and fiber for steadier recovery—"
            f"always follow your clinician’s instructions for treating lows.{trend_note}"
        )
    if gsm.state == "unknown_no_data":
        return (
            f"We don’t have enough readings yet to personalize tightly. “{meal_title}” is a sensible balanced option; "
            "log glucose on this page for sharper guidance next time."
        )
    return (
        f"Your pattern looks relatively controlled. “{meal_title}” keeps protein and fiber in the picture while staying mindful of carbs.{trend_note} "
        "Portions still matter—adjust with your dietitian."
    )


def _alternatives(
    ranked: List[ScoredCandidate],
    gsm: GlucoseStateModel,
    used_ids: set,
    n: int = 3,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for _ in range(n):
        filtered = [sc for sc in ranked if sc.food.id not in used_ids]
        if len(filtered) < 1:
            break
        buckets = _bucket_by_ranked(filtered)
        foods, mtype = _compose_meal_from_buckets(buckets, gsm)
        if not foods:
            break
        for f in foods:
            used_ids.add(f.id)
        title = _meal_title(foods)
        out.append(
            {
                "meal": title,
                "meal_type": mtype,
                "reason": _reason_next_meal(gsm),
                "highlights": _highlights(gsm)[:3],
                "feedback_food_id": foods[0].id,
            }
        )
    return out


def build_user_guidance(
    ranked: List[ScoredCandidate],
    gsm: GlucoseStateModel,
    text_ctx: Dict[str, str],
) -> Dict[str, Any]:
    """
    Primary user-facing payload: next meal, alternatives, avoid, plain-language explanation.
    No raw scores or internal weights.
    """
    hour = datetime.utcnow().hour
    level = _user_facing_glucose_level(gsm)

    buckets = _bucket_by_ranked(ranked)
    primary_foods, meal_type = _compose_meal_from_buckets(buckets, gsm)
    if not primary_foods and ranked:
        primary_foods = [ranked[0].food]
    meal_title = _meal_title(primary_foods)
    primary_id = primary_foods[0].id if primary_foods else None

    used = {f.id for f in primary_foods}
    alts = _alternatives(ranked, gsm, used, n=3)

    next_action = {
        "meal_type": meal_type,
        "meal": meal_title,
        "reason": _reason_next_meal(gsm),
        "priority": "eat_now",
        "priority_label": "Recommended now",
        "when_to_eat": _when_to_eat(hour, gsm),
        "highlights": _highlights(gsm),
        "feedback_food_id": primary_id,
    }

    explanation = _narrative_explanation(gsm, text_ctx, meal_title)

    return {
        "current_state": level,
        "next_action": next_action,
        "alternatives": alts,
        "avoid": _avoid_list(level, gsm),
        "explanation": explanation,
    }


def _bucket_by_ranked(ranked: List[ScoredCandidate]) -> Dict[str, List[FoodItem]]:
    buckets: Dict[str, List[FoodItem]] = defaultdict(list)
    seen: set = set()
    for sc in ranked:
        if sc.food.id in seen:
            continue
        seen.add(sc.food.id)
        role = _macro_role(sc.food)
        buckets[role].append(sc.food)
    return buckets
