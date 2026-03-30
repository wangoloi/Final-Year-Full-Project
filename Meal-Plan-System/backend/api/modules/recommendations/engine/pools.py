"""
Stage 3: Multi-pool candidate generation (strict / balanced / exploratory).
Caches merged (food_id, pool) rows for 60s — rehydrates FoodItem rows per DB session.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.models import FoodItem

from api.modules.recommendations.engine.constraints import MealConstraints
from api.modules.recommendations.engine import pool_cache


def _fetch_pool(
    db: Session,
    max_gi: int,
    diabetes_only: bool,
    limit: int,
) -> List[FoodItem]:
    q = db.query(FoodItem).filter(or_(FoodItem.glycemic_index.is_(None), FoodItem.glycemic_index <= max_gi))
    if diabetes_only:
        q = q.filter_by(diabetes_friendly=True)
    return q.order_by(FoodItem.glycemic_index.asc(), FoodItem.fiber.desc()).limit(limit).all()


def _rehydrate_from_rows(
    db: Session, rows: List[Dict[str, Any]]
) -> Tuple[Dict[str, List[FoodItem]], List[FoodItem], List[Tuple[FoodItem, str]]]:
    ids = [r["food_id"] for r in rows]
    if not ids:
        return {"strict": [], "balanced": [], "exploratory": []}, [], []
    foods = db.query(FoodItem).filter(FoodItem.id.in_(ids)).all()
    id_map = {f.id: f for f in foods}
    merged_tuples: List[Tuple[FoodItem, str]] = []
    for r in rows:
        f = id_map.get(r["food_id"])
        if f:
            merged_tuples.append((f, r["pool"]))
    pools: Dict[str, List[FoodItem]] = {"strict": [], "balanced": [], "exploratory": []}
    for f, p in merged_tuples:
        if p in pools:
            pools[p].append(f)
    merged = [f for f, _ in merged_tuples]
    return pools, merged, merged_tuples


def build_candidate_pools(
    db: Session,
    constraints: MealConstraints,
    pool_limit_each: int = 80,
) -> Tuple[Dict[str, List[FoodItem]], List[FoodItem], List[Tuple[FoodItem, str]], bool]:
    """
    Returns (labeled_pools, merged_unique_ordered, merged_tuples, cache_hit).
    """
    strict_gi = max(30, constraints.max_gi - 8)
    balanced_gi = constraints.max_gi
    exploratory_gi = min(75, constraints.max_gi + constraints.exploratory_gi_relax)

    strict_df = True
    balanced_df = constraints.prefer_diabetes_friendly
    exploratory_df = False

    cache_key = {
        "strict_gi": strict_gi,
        "balanced_gi": balanced_gi,
        "exploratory_gi": exploratory_gi,
        "strict_df": strict_df,
        "balanced_df": balanced_df,
        "exploratory_df": exploratory_df,
        "lim": pool_limit_each,
    }

    cached_rows = pool_cache.get_serialized_pool_rows(cache_key)
    if cached_rows is not None:
        pools, merged, merged_tuples = _rehydrate_from_rows(db, cached_rows)
        if merged_tuples:
            return pools, merged, merged_tuples, True

    strict = _fetch_pool(db, strict_gi, strict_df, pool_limit_each)
    if len(strict) < pool_limit_each // 4:
        strict = _fetch_pool(db, strict_gi, False, pool_limit_each)

    balanced = _fetch_pool(db, balanced_gi, balanced_df, pool_limit_each)
    if len(balanced) < pool_limit_each // 4 and balanced_df:
        balanced = _fetch_pool(db, balanced_gi, False, pool_limit_each)

    exploratory = _fetch_pool(db, exploratory_gi, exploratory_df, pool_limit_each)

    pools = {
        "strict": strict,
        "balanced": balanced,
        "exploratory": exploratory,
    }

    seen: Set[int] = set()
    merged: List[FoodItem] = []
    merged_tuples: List[Tuple[FoodItem, str]] = []
    for label in ("strict", "balanced", "exploratory"):
        for f in pools[label]:
            if f.id not in seen:
                seen.add(f.id)
                merged.append(f)
                merged_tuples.append((f, label))

    serialized = [{"food_id": f.id, "pool": p} for f, p in merged_tuples]
    pool_cache.set_serialized_pool_rows(cache_key, serialized)

    return pools, merged, merged_tuples, False
