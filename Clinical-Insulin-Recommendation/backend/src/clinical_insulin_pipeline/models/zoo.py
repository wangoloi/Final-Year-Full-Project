"""Production-focused regressors: RandomForest, HistGradientBoosting, XGBoost."""
from __future__ import annotations

from typing import Any, List, Tuple

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from xgboost import XGBRegressor

from ..config import RANDOM_STATE


def build_model_factories() -> List[Tuple[str, Any]]:
    """Three strong tabular baselines for insulin dose regression (see docs)."""
    return [
        (
            "random_forest",
            RandomForestRegressor(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=2,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
        (
            "hist_gradient_boosting",
            HistGradientBoostingRegressor(
                max_depth=6,
                learning_rate=0.05,
                max_iter=500,
                random_state=RANDOM_STATE,
                early_stopping=True,
                validation_fraction=0.12,
                n_iter_no_change=30,
            ),
        ),
        (
            "xgboost",
            XGBRegressor(
                n_estimators=500,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                reg_lambda=1.0,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
    ]


def get_feature_importance_vector(model: Any, n_features: int) -> np.ndarray | None:
    if hasattr(model, "feature_importances_"):
        return np.asarray(model.feature_importances_, dtype=float)
    if hasattr(model, "coef_"):
        c = np.asarray(model.coef_).ravel()
        if c.size == n_features:
            return np.abs(c)
    return None
