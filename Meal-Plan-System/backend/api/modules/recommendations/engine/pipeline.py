"""
Orchestrates recommendation stages; user-facing output is guidance-centric (no raw scores).
"""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from api.models import FoodItem, User

from api.modules.glucose.repository import list_readings
from api.modules.recommendations.engine.context_model import GlucoseStateModel, glucose_state_to_dict, infer_glucose_state
from api.modules.recommendations.engine.constraints import generate_constraints
from api.modules.recommendations.engine.pools import build_candidate_pools
from api.modules.recommendations.engine.optimization import ScoredCandidate, assign_weekly_plan, optimize_top_n
from api.modules.recommendations.engine.meal_guidance import build_user_guidance
from api.modules.recommendations.feedback_repository import get_like_avoid_counts


def _food_to_dict(food: FoodItem) -> Dict[str, Any]:
    return {
        "id": str(food.id),
        "name": food.name,
        "local_name": food.local_name,
        "category": food.category,
        "calories": float(food.calories),
        "protein": float(food.protein),
        "carbs": float(food.carbohydrates),
        "fat": float(food.fat),
        "fiber": float(food.fiber or 0),
        "glycemic_index": food.glycemic_index,
        "diabetes_friendly": food.diabetes_friendly,
    }


def _ensure_week_ranked(ranked: List[ScoredCandidate], min_n: int = 28) -> List[ScoredCandidate]:
    if len(ranked) >= min_n:
        return ranked
    if not ranked:
        return ranked
    out = list(ranked)
    i = 0
    while len(out) < min_n:
        out.append(ranked[i % len(ranked)])
        i += 1
    return out


def _legacy_tier(gsm: GlucoseStateModel) -> str:
    m = {
        "falling_low": "below_range",
        "stable_controlled": "in_range",
        "improving": "in_range",
        "elevated": "above_range",
        "rising_high": "above_range",
        "critical_high": "high",
        "unknown_no_data": "unknown",
    }
    return m.get(gsm.state, "in_range")


def _weekly_slot_line(gsm: GlucoseStateModel, slot_key: str) -> str:
    if gsm.state in ("critical_high", "rising_high", "elevated"):
        if slot_key == "snack":
            return "Choose a small, fiber-forward snack with some protein."
        return "Lean protein plus vegetables helps blunt post-meal rises."
    if gsm.state == "falling_low":
        return "Pair carbs with protein; follow your care plan for lows."
    if gsm.state == "unknown_no_data":
        return "Balanced plate—log glucose for more tailored ideas."
    return "Balance protein, fiber, and sensible carbs for this meal."


def run_recommendation_pipeline(db: Session, user: User, limit: int) -> Dict[str, Any]:
    readings = list_readings(db, user.id, limit=20)
    gsm, text_ctx = infer_glucose_state(readings)
    constraints = generate_constraints(gsm, user)
    pools, _merged, merged_tuples, _pool_cache_hit = build_candidate_pools(db, constraints, pool_limit_each=80)

    liked, avoided = get_like_avoid_counts(db, user.id)

    n_cand = len(merged_tuples)
    target_ranked = min(120, n_cand) if n_cand else 0
    ranked = optimize_top_n(merged_tuples, gsm, constraints, liked, avoided, target_n=max(target_ranked, min(28, n_cand)))

    guidance = build_user_guidance(ranked, gsm, text_ctx)

    week_ranked = _ensure_week_ranked(ranked, 28)
    weekly_assignments = assign_weekly_plan(week_ranked)

    weekly_plan = []
    for a in weekly_assignments:
        fd = a.get("food")
        entry: Dict[str, Any] = {
            "day": a["day"],
            "slot_key": a["slot_key"],
            "slot_label": a["slot_label"],
            "food": _food_to_dict(fd) if fd else None,
            "guidance_line": _weekly_slot_line(gsm, a.get("slot_key") or ""),
        }
        weekly_plan.append(entry)

    glucose_state = glucose_state_to_dict(gsm)

    glucose_context = {
        "tier": _legacy_tier(gsm),
        "rationale": text_ctx["rationale"],
        "readings_used": glucose_state["readings_analyzed"],
        "latest_mg_dl": glucose_state.get("latest_mg_dl"),
        "avg_recent_mg_dl": glucose_state.get("avg_recent_mg_dl"),
        "glucose_state": glucose_state,
    }

    return {
        "engine_version": "3.0",
        "guidance": guidance,
        "weekly_plan": weekly_plan,
        "glucose_context": glucose_context,
    }
