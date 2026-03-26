"""Validation-driven selection of feature count N (train-only MI ranking, regression target)."""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from smart_sensor_ml import config
from smart_sensor_ml.evaluate_model import evaluate_regression_model
from smart_sensor_ml.preprocess import PreprocessPipeline

logger = logging.getLogger(__name__)


def _y_reg(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").values.astype(float)


def select_best_feature_count(
    pre: PreprocessPipeline,
    train_df,
    val_df,
    random_state: int = 42,
) -> Tuple[int, List[Dict[str, float]]]:
    """
    Try candidate N values; fit a fast gradient boosting regressor on train, maximize **validation R²**.
    """
    y_train = _y_reg(train_df[config.COL_TARGET])
    y_val = _y_reg(val_df[config.COL_TARGET])

    max_n = len(pre.mi_ranked_final)
    candidates = sorted({n for n in config.FEATURE_COUNT_CANDIDATES if n <= max_n} | {max_n})
    if not candidates:
        candidates = [max_n]

    rows: List[Dict[str, float]] = []
    best_n, best_r2 = candidates[0], -1e9

    for n in candidates:
        pre.select_top_n(n, train_df)
        X_tr = pre.transform(train_df)
        X_va = pre.transform(val_df)
        reg = GradientBoostingRegressor(
            n_estimators=120,
            max_depth=3,
            learning_rate=0.08,
            subsample=0.9,
            random_state=random_state,
        )
        reg.fit(X_tr, y_train)
        ev = evaluate_regression_model(reg, X_va, y_val, model_name="probe")
        rows.append({"n_features": float(n), "val_r2": float(ev.r2), "val_rmse": float(ev.rmse), "val_mae": float(ev.mae)})
        if ev.r2 > best_r2:
            best_r2 = ev.r2
            best_n = n
        logger.info("Feature-count probe: N=%s → val R²=%.4f RMSE=%.4f", n, ev.r2, ev.rmse)

    logger.info("Chosen feature count N=%s (best validation R²=%.4f)", best_n, best_r2)
    return best_n, rows
