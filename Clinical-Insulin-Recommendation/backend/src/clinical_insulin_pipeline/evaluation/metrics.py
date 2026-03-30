"""Regression metrics including MAPE-safe for zero targets."""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
from sklearn import metrics as skm


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    mae = float(skm.mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(skm.mean_squared_error(y_true, y_pred)))
    r2 = float(skm.r2_score(y_true, y_pred))
    max_err = float(skm.max_error(y_true, y_pred))
    eps = 1e-6
    denom = np.maximum(np.abs(y_true), eps)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)
    return {
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "r2": r2,
        "max_error": max_err,
    }


def metrics_to_row(name: str, m: Dict[str, float]) -> Dict[str, Any]:
    return {"model": name, **m}
