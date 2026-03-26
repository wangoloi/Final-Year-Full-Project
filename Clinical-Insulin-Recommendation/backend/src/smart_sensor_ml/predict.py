"""7. Prediction — single-row or batch inference with fitted preprocessor + model."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

import numpy as np
import pandas as pd

from smart_sensor_ml import config
from smart_sensor_ml.preprocess import PreprocessPipeline, insulin_dose_to_tier_name


def predict(
    model: Any,
    preprocessor: PreprocessPipeline,
    X_raw: pd.DataFrame,
) -> np.ndarray:
    """Return predicted continuous insulin dose."""
    Xt = preprocessor.transform(X_raw)
    return model.predict(Xt)


def predict_with_explanation(
    model: Any,
    preprocessor: PreprocessPipeline,
    row: Mapping[str, Any],
    feature_importance: Optional[np.ndarray] = None,
    feature_names: Optional[List[str]] = None,
    insulin_bin_edges: Optional[np.ndarray] = None,
    train_insulin_mean: Optional[float] = None,
    train_insulin_std: Optional[float] = None,
) -> Dict[str, Any]:
    """
    One observation as dict -> predicted dose + optional tier label (from train tertile edges).
    """
    df = pd.DataFrame([dict(row)])
    pred = predict(model, preprocessor, df)
    dose = float(pred.ravel()[0])
    edges = insulin_bin_edges if insulin_bin_edges is not None else preprocessor.insulin_bin_edges
    tier_idx, tier_name = insulin_dose_to_tier_name(dose, edges)

    out: Dict[str, Any] = {
        "predicted_insulin_dose": dose,
        "predicted_tier_index": tier_idx,
        "predicted_tier_name": tier_name,
        "task": "regression",
    }
    # Heuristic confidence from distance to training dose distribution (not a calibrated prob)
    mean = float(train_insulin_mean) if train_insulin_mean is not None else dose
    std = float(train_insulin_std) if train_insulin_std is not None and train_insulin_std > 1e-9 else 1.0
    z = abs(dose - mean) / max(std, 1e-6)
    conf = float(max(0.15, min(0.98, 1.0 / (1.0 + z))))
    rest = (1.0 - conf) / max(len(config.CLASS_NAMES) - 1, 1)
    out["confidence"] = conf
    out["class_probabilities"] = {
        config.CLASS_NAMES[i]: conf if i == tier_idx else rest for i in range(config.N_CLASSES)
    }
    if feature_importance is not None and feature_names:
        x = preprocessor.transform(df).ravel()
        contrib = np.abs(x) * np.asarray(feature_importance).ravel()[: len(x)]
        top = np.argsort(contrib)[::-1][:8]
        out["top_contributing_features"] = [
            {"feature": feature_names[i], "score": float(contrib[i])} for i in top if contrib[i] > 0
        ]
    return out

