"""Regression metrics used for model evaluation and selection."""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
from sklearn import metrics as skm


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    mae = float(skm.mean_absolute_error(y_true, y_pred))
    mse = float(skm.mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(skm.r2_score(y_true, y_pred))
    return {
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2": r2,
    }


def metrics_to_row(name: str, m: Dict[str, float]) -> Dict[str, Any]:
    return {"model": name, **m}
