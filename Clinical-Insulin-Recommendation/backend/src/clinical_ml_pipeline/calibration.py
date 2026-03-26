"""
Probability calibration for clinical ML pipeline.

Uses sklearn's CalibratedClassifierCV with:
- Platt Scaling (sigmoid)
- Isotonic Regression (isotonic)

Calibration occurs after model training and before threshold optimization.
Uses cross-validation (cv="prefit" with held-out calibration set) to prevent data leakage.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

import numpy as np
from sklearn.calibration import CalibratedClassifierCV

logger = logging.getLogger(__name__)

# Sigmoid (Platt), isotonic, and temperature (sklearn 1.8+)
CALIBRATION_METHODS = ("sigmoid", "isotonic", "temperature")


def _get_calibration_data(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: Optional[np.ndarray],
    y_val: Optional[np.ndarray],
    cal_ratio: float = 0.2,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get calibration set: use validation if available, else split from train.
    """
    if X_val is not None and y_val is not None and len(X_val) > 0:
        return X_val, y_val
    from sklearn.model_selection import train_test_split
    _, X_cal, _, y_cal = train_test_split(
        X_train, y_train, test_size=cal_ratio, stratify=y_train, random_state=random_state
    )
    return X_cal, y_cal


def _unwrap_label_encoder(estimator: Any) -> Tuple[Any, Optional[Any]]:
    """If estimator is _LabelEncoderWrapper, return (inner_estimator, le). Else (estimator, None)."""
    cls_name = type(estimator).__name__
    if cls_name == "_LabelEncoderWrapper" and hasattr(estimator, "estimator"):
        return estimator.estimator, getattr(estimator, "le", None)
    return estimator, None


def _wrap_label_encoder(estimator: Any, le: Any) -> Any:
    """Wrap estimator with LabelEncoder for string output."""
    if le is None:
        return estimator
    return _LabelEncoderWrapper(estimator, le)


class _LabelEncoderWrapper:
    """Wraps estimator to return string labels when trained on encoded y."""

    _estimator_type = "classifier"

    def __init__(self, estimator: Any, label_encoder: Any):
        self.estimator = estimator
        self.le = label_encoder
        self.classes_ = np.array(label_encoder.classes_)

    def get_params(self, deep: bool = True) -> dict:
        """Sklearn-compatible get_params for cloning."""
        return {"estimator": self.estimator, "label_encoder": self.le}

    def set_params(self, **params) -> "_LabelEncoderWrapper":
        """Sklearn-compatible set_params."""
        if "estimator" in params:
            self.estimator = params["estimator"]
        if "label_encoder" in params:
            self.le = params["label_encoder"]
            self.classes_ = np.array(self.le.classes_)
        return self

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs) -> "_LabelEncoderWrapper":
        """Forward fit to inner estimator (for sklearn compatibility)."""
        self.estimator.fit(X, y, **kwargs)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        pred = self.estimator.predict(X)
        return self.le.inverse_transform(pred.astype(int))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict_proba(X)


def wrap_with_calibration(
    estimator: Any,
    X_cal: np.ndarray,
    y_cal: np.ndarray,
    method: str = "sigmoid",
    cv: int = 5,
) -> Any:
    """
    Wrap a fitted estimator with probability calibration.

    Uses CalibratedClassifierCV with cv="prefit" so the base estimator is
    already fitted; calibration is fit on the held-out calibration set.

    Handles _LabelEncoderWrapper: calibrates the inner estimator (which outputs
    integer indices), then re-wraps for string label output.

    Args:
        estimator: Fitted estimator with predict_proba (may be _LabelEncoderWrapper).
        X_cal: Calibration features.
        y_cal: Calibration labels (strings or encoded; must match estimator's classes).
        method: "sigmoid" (Platt) or "isotonic".
        cv: Ignored (uses prefit).

    Returns:
        Calibrated estimator (possibly wrapped with LabelEncoder).
    """
    if method not in CALIBRATION_METHODS:
        raise ValueError(f"method must be one of {CALIBRATION_METHODS}, got {method}")

    inner_est, le = _unwrap_label_encoder(estimator)
    if not hasattr(inner_est, "predict_proba"):
        logger.warning("Estimator has no predict_proba; skipping calibration")
        return estimator

    # Use encoded y for calibration when we have LabelEncoder (inner model uses int indices)
    if le is not None:
        y_cal_enc = le.transform(np.asarray(y_cal).astype(str))
    else:
        y_cal_enc = y_cal

    try:
        from sklearn.frozen import FrozenEstimator
        base_for_cal = FrozenEstimator(inner_est)
        use_prefit = False
    except ImportError:
        base_for_cal = inner_est
        use_prefit = True

    # Temperature scaling requires sklearn 1.8+; fallback to sigmoid if unavailable
    if method == "temperature":
        try:
            calibrated = CalibratedClassifierCV(base_for_cal, method="temperature")
            calibrated.fit(X_cal, y_cal_enc)
            logger.info("Applied temperature calibration")
            return _wrap_label_encoder(calibrated, le)
        except (TypeError, ValueError) as e:
            logger.warning("Temperature calibration not available (sklearn 1.8+): %s. Using sigmoid.", e)
            method = "sigmoid"

    calibrated = (
        CalibratedClassifierCV(base_for_cal, method=method, cv="prefit")
        if use_prefit
        else CalibratedClassifierCV(base_for_cal, method=method)
    )
    calibrated.fit(X_cal, y_cal_enc)
    logger.info("Applied %s calibration", method)
    return _wrap_label_encoder(calibrated, le)
