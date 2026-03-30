"""
Stage 7: Natural-language explanations per recommendation (educational).
"""
from __future__ import annotations

from typing import Tuple

from api.models import FoodItem

from api.modules.recommendations.engine.context_model import GlucoseStateModel


def explain_food(food: FoodItem, gsm: GlucoseStateModel, pool_name: str, score_total: float) -> Tuple[str, str]:
    """
    Returns (health_badge, one_line_explanation).
    """
    gi = food.glycemic_index
    fiber = food.fiber or 0
    carbs = food.carbohydrates or 0
    protein = food.protein or 0

    badge = "Balanced choice"
    if gsm.state in ("critical_high", "rising_high", "elevated"):
        if gi is not None and gi <= 40 and carbs <= 38:
            badge = "Best for high glucose"
        elif fiber >= 5:
            badge = "Fiber-forward"
        else:
            badge = "Moderate glycemic impact"
    elif gsm.state == "falling_low":
        badge = "Steady energy"
    elif pool_name == "strict":
        badge = "Strictly matched"
    elif pool_name == "exploratory":
        badge = "Discovery pick"

    parts = []
    if gi is not None:
        parts.append(f"GI near {gi}")
    parts.append(f"~{carbs:.0f}g carbs / {protein:.0f}g protein")
    if fiber >= 3:
        parts.append(f"{fiber:.0f}g fiber supports steadier glucose")
    if gsm.trend == "increasing" and gi is not None and gi <= 45:
        parts.append("lower glycemic load fits a rising trend")
    elif gsm.stability == "unstable" and fiber >= 4:
        parts.append("higher fiber may blunt swings")

    line = "; ".join(parts[:3]) + "."
    if score_total >= 0.55:
        line = "Strong match for your current glucose pattern: " + line
    else:
        line = "Reasonable option given your constraints: " + line

    return badge, line
