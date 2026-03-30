"""
Stage 4: Multi-factor weighted scoring with state-adaptive weights.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from api.models import FoodItem

from api.modules.recommendations.engine.constraints import MealConstraints
from api.modules.recommendations.engine.context_model import GlucoseStateModel


@dataclass
class ScoreBreakdown:
    glycemic: float
    fiber: float
    protein_balance: float
    personalization: float
    context_alignment: float
    diversity_slot: float
    repetition_penalty: float
    pool_boost: float
    total: float


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def adaptive_weights(gsm: GlucoseStateModel) -> Dict[str, float]:
    """Higher weight on glycemic/context when risk is high."""
    r = gsm.risk_score
    return {
        "w_glycemic": 0.22 + 0.18 * r,
        "w_fiber": 0.14 + 0.06 * r,
        "w_protein": 0.12 + 0.04 * (1 - r * 0.5),
        "w_personalization": 0.10 + 0.05 * (1 - r),
        "w_context": 0.22 + 0.15 * r,
        "w_diversity": 0.08,
        "w_repetition": 0.12 + 0.08 * r,
        "w_pool": 0.06,
    }


def personalization_score(food_id: int, liked: Dict[int, int], avoided: Dict[int, int]) -> float:
    likes = liked.get(food_id, 0)
    avoids = avoided.get(food_id, 0)
    raw = 0.15 * likes - 0.2 * avoids
    return _clamp01(0.5 + raw)


def score_food_multi(
    food: FoodItem,
    gsm: GlucoseStateModel,
    constraints: MealConstraints,
    pool_name: str,
    liked: Dict[int, int],
    avoided: Dict[int, int],
    recent_duplicate_count: int,
) -> Tuple[float, ScoreBreakdown]:
    gi = float(food.glycemic_index or 55)
    glycemic = _clamp01(1.0 - (gi / 100.0))
    fiber = float(food.fiber or 0)
    fiber_s = _clamp01(fiber / 12.0)
    carbs = float(food.carbohydrates or 0)
    protein = float(food.protein or 0)
    protein_balance = _clamp01(protein / 35.0) * (1.0 - _clamp01(carbs / 80.0) * 0.3)

    # Context alignment: penalize carbs above soft max; reward fiber floor
    ca = 1.0
    if carbs > constraints.carb_soft_max_g:
        ca -= _clamp01((carbs - constraints.carb_soft_max_g) / 40.0) * 0.6
    if fiber < constraints.fiber_floor_g:
        ca -= _clamp01((constraints.fiber_floor_g - fiber) / 5.0) * 0.35
    if gsm.state in ("critical_high", "rising_high", "elevated") and carbs > 45:
        ca -= 0.15
    ca = _clamp01(ca)

    pers = personalization_score(food.id, liked, avoided)

    pool_boost = {"strict": 0.12, "balanced": 0.06, "exploratory": 0.0}.get(pool_name, 0.03)

    rep_pen = _clamp01(0.15 * recent_duplicate_count)

    w = adaptive_weights(gsm)
    diversity_slot = 0.5  # placeholder; optimization layer adjusts via repetition_penalty

    total = (
        w["w_glycemic"] * glycemic
        + w["w_fiber"] * fiber_s
        + w["w_protein"] * protein_balance
        + w["w_personalization"] * pers
        + w["w_context"] * ca
        + w["w_diversity"] * diversity_slot
        + w["w_pool"] * (pool_boost * 8.0)  # scale pool boost to 0..~1
        - w["w_repetition"] * rep_pen
    )

    bd = ScoreBreakdown(
        glycemic=glycemic,
        fiber=fiber_s,
        protein_balance=protein_balance,
        personalization=pers,
        context_alignment=ca,
        diversity_slot=diversity_slot,
        repetition_penalty=rep_pen,
        pool_boost=pool_boost,
        total=float(total),
    )
    return total, bd


def breakdown_to_dict(b: ScoreBreakdown) -> Dict[str, Any]:
    return {
        "glycemic": round(b.glycemic, 4),
        "fiber": round(b.fiber, 4),
        "protein_balance": round(b.protein_balance, 4),
        "personalization": round(b.personalization, 4),
        "context_alignment": round(b.context_alignment, 4),
        "diversity_slot": round(b.diversity_slot, 4),
        "repetition_penalty": round(b.repetition_penalty, 4),
        "pool_boost": round(b.pool_boost, 4),
        "total": round(b.total, 4),
    }
