"""
Stage 2: Dynamic constraint generation from glucose state + user profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from api.models import User

from api.modules.recommendations.engine.context_model import GlucoseStateModel


@dataclass
class MealConstraints:
    max_gi: int
    carb_soft_max_g: float
    fiber_floor_g: float
    prefer_diabetes_friendly: bool
    exploratory_gi_relax: int  # added to max_gi for exploratory pool only


def generate_constraints(gsm: GlucoseStateModel, user: User) -> MealConstraints:
    base = 50 if user.has_diabetes else 55
    if gsm.state == "unknown_no_data":
        return MealConstraints(
            max_gi=base,
            carb_soft_max_g=55.0,
            fiber_floor_g=2.0,
            prefer_diabetes_friendly=bool(user.has_diabetes),
            exploratory_gi_relax=8,
        )

    if gsm.state in ("critical_high", "rising_high"):
        mg = max(35, base - 12)
        return MealConstraints(
            max_gi=min(40, mg),
            carb_soft_max_g=32.0,
            fiber_floor_g=4.0,
            prefer_diabetes_friendly=True,
            exploratory_gi_relax=4,
        )

    if gsm.state == "elevated":
        return MealConstraints(
            max_gi=max(38, base - 10),
            carb_soft_max_g=40.0,
            fiber_floor_g=3.5,
            prefer_diabetes_friendly=True,
            exploratory_gi_relax=6,
        )

    if gsm.state == "falling_low":
        return MealConstraints(
            max_gi=min(55, base + 5),
            carb_soft_max_g=58.0,
            fiber_floor_g=2.0,
            prefer_diabetes_friendly=bool(user.has_diabetes),
            exploratory_gi_relax=10,
        )

    if gsm.state == "improving":
        return MealConstraints(
            max_gi=base,
            carb_soft_max_g=48.0,
            fiber_floor_g=2.5,
            prefer_diabetes_friendly=bool(user.has_diabetes),
            exploratory_gi_relax=8,
        )

    # stable_controlled
    return MealConstraints(
        max_gi=base,
        carb_soft_max_g=50.0,
        fiber_floor_g=2.5,
        prefer_diabetes_friendly=bool(user.has_diabetes),
        exploratory_gi_relax=8,
    )


def constraints_to_dict(c: MealConstraints) -> Dict[str, Any]:
    return {
        "max_gi": c.max_gi,
        "carb_soft_max_g": c.carb_soft_max_g,
        "fiber_floor_g": c.fiber_floor_g,
        "prefer_diabetes_friendly": c.prefer_diabetes_friendly,
        "exploratory_gi_relax": c.exploratory_gi_relax,
    }
