"""
Stage 5: Constrained selection — diversity + no short-window repeats + weekly assignment.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from api.models import FoodItem

from api.modules.recommendations.engine.scoring import ScoreBreakdown, score_food_multi
from api.modules.recommendations.engine.constraints import MealConstraints
from api.modules.recommendations.engine.context_model import GlucoseStateModel


@dataclass
class ScoredCandidate:
    food: FoodItem
    pool_name: str
    total: float
    breakdown: ScoreBreakdown


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = [
    ("breakfast", "Breakfast"),
    ("lunch", "Lunch"),
    ("dinner", "Dinner"),
    ("snack", "Snack"),
]


def slot_affinity(food: FoodItem, slot_key: str) -> float:
    cal = food.calories or 0
    p = food.protein or 0
    if slot_key == "snack" and cal <= 220:
        return 0.08
    if slot_key == "dinner" and p >= 18:
        return 0.06
    if slot_key == "breakfast" and cal <= 450:
        return 0.04
    return 0.0


def diversify_scored(scored: List[ScoredCandidate], limit: int) -> List[ScoredCandidate]:
    """Round-robin across categories by descending score within each category."""
    by_cat: Dict[str, List[ScoredCandidate]] = defaultdict(list)
    for s in sorted(scored, key=lambda x: -x.total):
        cat = (s.food.category or "other").lower()
        by_cat[cat].append(s)

    cats = list(by_cat.keys())
    out: List[ScoredCandidate] = []
    idx = 0
    while len(out) < limit and any(by_cat[c] for c in cats):
        c = cats[idx % len(cats)]
        if by_cat[c]:
            out.append(by_cat[c].pop(0))
        idx += 1
    if len(out) < limit:
        seen = {s.food.id for s in out}
        for s in sorted(scored, key=lambda x: -x.total):
            if len(out) >= limit:
                break
            if s.food.id not in seen:
                out.append(s)
                seen.add(s.food.id)
    return out[:limit]


def optimize_top_n(
    merged: List[Tuple[FoodItem, str]],
    gsm: GlucoseStateModel,
    constraints: MealConstraints,
    liked: Dict[int, int],
    avoided: Dict[int, int],
    target_n: int,
) -> List[ScoredCandidate]:
    scored: List[ScoredCandidate] = []
    for food, pool_name in merged:
        total, bd = score_food_multi(food, gsm, constraints, pool_name, liked, avoided, 0)
        scored.append(ScoredCandidate(food=food, pool_name=pool_name, total=total, breakdown=bd))
    return diversify_scored(scored, target_n)


def assign_weekly_plan(
    ranked: List[ScoredCandidate],
    window: int = 6,
) -> List[Dict[str, Any]]:
    """
    Assign 28 meal slots avoiding repeated foods within a sliding window where possible.
    Uses an extended rotating candidate list built from ranked scores.
    """
    slots_order: List[Tuple[str, str, str]] = []
    for day in DAYS:
        for key, label in SLOTS:
            slots_order.append((day, key, label))

    if not ranked:
        return [
            {"day": d, "slot_key": k, "slot_label": l, "food": None, "pool": None, "score": None}
            for d, k, l in slots_order
        ]

    extended = list(ranked)
    while len(extended) < 40:
        extended.extend(ranked)

    recent: deque = deque(maxlen=window)
    assigned: List[Dict[str, Any]] = []
    scan_start = 0

    for day, slot_key, label in slots_order:
        best: Tuple[float, int, ScoredCandidate] | None = None
        for attempt in range(len(extended)):
            idx = (scan_start + attempt) % len(extended)
            sc = extended[idx]
            if sc.food.id in recent:
                continue
            val = sc.total + slot_affinity(sc.food, slot_key)
            if best is None or val > best[0]:
                best = (val, idx, sc)
        if best is not None:
            _, pick_idx, chosen = best
            scan_start = pick_idx + 1
        else:
            chosen = extended[scan_start % len(extended)]
            scan_start += 1

        recent.append(chosen.food.id)
        assigned.append(
            {
                "day": day,
                "slot_key": slot_key,
                "slot_label": label,
                "food": chosen.food,
                "pool": chosen.pool_name,
                "score": round(chosen.total, 4),
            }
        )

    return assigned
