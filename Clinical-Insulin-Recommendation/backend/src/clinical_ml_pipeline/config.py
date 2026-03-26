"""
Clinical ML Pipeline Configuration.

Centralizes settings for imbalance strategies, models, tuning, and evaluation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

# Models to train (tree-based focus; LR/SVM excluded per experiment findings)
DEFAULT_MODELS: Tuple[str, ...] = (
    "gradient_boosting",
    "random_forest",
    "extra_trees",
    "balanced_rf",
    "lightgbm",
    "catboost",
    "mlp",
)

# Imbalance strategies (SMOTE removed - experiments showed it hurts performance)
IMBALANCE_STRATEGIES: Tuple[str, ...] = (
    "class_weight",
    "cost_sensitive",
    "balanced_rf",  # Uses BalancedRandomForestClassifier
)

# Clinical cost matrix (from schema)
CLINICAL_COST_MATRIX = {
    "down": {"down": 0, "up": 5, "steady": 1, "no": 1},
    "up": {"down": 5, "up": 0, "steady": 1, "no": 1},
    "steady": {"down": 2, "up": 2, "steady": 0, "no": 0.5},
    "no": {"down": 3, "up": 2, "steady": 0.5, "no": 0},
}

RANDOM_STATE = 42
CV_FOLDS = 5
OPTUNA_TRIALS = 80  # Increased from 40 for better hyperparameter search
EARLY_STOPPING_ROUNDS = 15

# Safety constraints: models must pass these to be eligible for selection
MIN_F1_MACRO = 0.35  # Avoid models that ignore minority classes
MAX_CLINICAL_COST = 0.8  # Reject models with too many risky misclassifications

# Model selection: rank-based (Borda-style). No arbitrary weights.
# For each metric, rank 1=better, 2=worse, 1.5=tie. Lower total rank wins.
# Higher is better: f1_weighted, roc_auc, f1_macro
# Lower is better: clinical_cost, overfitting_gap


def passes_safety_constraints(f1_macro: float, clinical_cost: float) -> bool:
    """True if model meets minimum safety requirements for selection."""
    return f1_macro >= MIN_F1_MACRO and clinical_cost <= MAX_CLINICAL_COST


def _rank_pair(val_a: float, val_b: float, higher_is_better: bool) -> Tuple[float, float]:
    """Return (rank_a, rank_b) for a pair. Lower rank = better."""
    if higher_is_better:
        better_a = val_a > val_b
        better_b = val_b > val_a
    else:
        better_a = val_a < val_b
        better_b = val_b < val_a
    if better_a and not better_b:
        return (1.0, 2.0)
    if better_b and not better_a:
        return (2.0, 1.0)
    return (1.5, 1.5)


def is_better_by_rank(
    f1_weighted_new: float,
    roc_auc_new: float,
    f1_macro_new: float,
    clinical_cost_new: float,
    overfitting_gap_new: float,
    f1_weighted_old: float,
    roc_auc_old: float,
    f1_macro_old: float,
    clinical_cost_old: float,
    overfitting_gap_old: float,
) -> bool:
    """
    Rank-based comparison: True if new candidate is better than old.
    Uses Borda-style ranking. Safety constraints: new must pass (f1_macro>=MIN, cost<=MAX)
    to be eligible. If old fails safety and new passes, new wins. If both pass, use rank.
    """
    new_passes = passes_safety_constraints(f1_macro_new, clinical_cost_new)
    old_passes = passes_safety_constraints(f1_macro_old, clinical_cost_old)
    if not new_passes and old_passes:
        return False  # Never select a model that fails safety when we have one that passes
    if new_passes and not old_passes:
        return True  # Prefer any safe model over unsafe
    # Both pass or both fail: use rank
    metrics_new = (f1_weighted_new, roc_auc_new, f1_macro_new, clinical_cost_new, overfitting_gap_new)
    metrics_old = (f1_weighted_old, roc_auc_old, f1_macro_old, clinical_cost_old, overfitting_gap_old)
    higher_better = (True, True, True, False, False)

    rank_new = 0.0
    rank_old = 0.0
    for (v_new, v_old), hb in zip(zip(metrics_new, metrics_old), higher_better):
        r_old, r_new = _rank_pair(v_old, v_new, hb)
        rank_old += r_old
        rank_new += r_new

    return rank_new < rank_old


def select_best_row_by_rank(df):
    """
    From a DataFrame of experiments, select the best row using Borda-style ranking.
    Only considers rows that pass safety constraints (f1_macro>=MIN, clinical_cost<=MAX).
    Higher is better: f1_weighted, roc_auc, f1_macro. Lower is better: clinical_cost, overfitting_gap.
    """
    import pandas as pd
    safe = df[
        (df["f1_macro"] >= MIN_F1_MACRO) & (df["clinical_cost"] <= MAX_CLINICAL_COST)
    ].copy()
    if safe.empty:
        safe = df.copy()  # Fallback: no model passes, use all
    out = safe.copy()
    # Higher is better: lower rank for higher values
    out["_r_f1"] = out["f1_weighted"].rank(ascending=False, method="average")
    out["_r_roc"] = out["roc_auc"].rank(ascending=False, method="average")
    out["_r_macro"] = out["f1_macro"].rank(ascending=False, method="average")
    # Lower is better: lower rank for lower values
    out["_r_cost"] = out["clinical_cost"].rank(ascending=True, method="average")
    out["_r_gap"] = out["overfitting_gap"].rank(ascending=True, method="average")
    out["_total_rank"] = out["_r_f1"] + out["_r_roc"] + out["_r_macro"] + out["_r_cost"] + out["_r_gap"]
    best_idx = out["_total_rank"].idxmin()
    return out.loc[best_idx]
