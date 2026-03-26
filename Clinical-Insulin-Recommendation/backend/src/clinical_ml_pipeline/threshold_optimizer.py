"""
Phase 5: Probability threshold optimization for cost-sensitive prediction.

Optimizes per-class thresholds to minimize clinical cost while maintaining F1.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import CLINICAL_COST_MATRIX

logger = logging.getLogger(__name__)


def _clinical_cost(y_true: np.ndarray, y_pred: List[str], labels: List[str]) -> float:
    """Compute average clinical cost."""
    total, n = 0.0, len(y_true)
    for i in range(n):
        t = str(y_true[i]).lower()
        p = str(y_pred[i]).lower()
        total += CLINICAL_COST_MATRIX.get(t, {}).get(p, 1.0)
    return total / n if n else float("nan")


def _predict_with_thresholds(
    proba: np.ndarray,
    labels: List[str],
    thresholds: np.ndarray,
) -> List[str]:
    """Predict using adjusted probabilities: proba[i] / (threshold[i] + eps)."""
    eps = 1e-6
    adj = proba / (thresholds + eps)
    pred_idx = np.argmax(adj, axis=1)
    return [labels[i] for i in pred_idx]


def optimize_thresholds_cost_sensitive(
    estimator: Any,
    X: np.ndarray,
    y_true: np.ndarray,
    labels: List[str],
    n_trials: int = 50,
) -> Tuple[np.ndarray, float, float]:
    """
    Optimize per-class thresholds to minimize clinical cost.

    Returns:
        (best_thresholds, best_cost, best_f1)
    """
    if not hasattr(estimator, "predict_proba"):
        return np.ones(len(labels)), float("nan"), float("nan")

    proba = estimator.predict_proba(X)
    n_classes = len(labels)
    best_cost = float("inf")
    best_f1 = 0.0
    best_thresholds = np.ones(n_classes)

    # Grid search over threshold combinations
    from sklearn.metrics import f1_score

    for _ in range(n_trials):
        thresholds = np.random.uniform(0.15, 0.5, n_classes)
        pred = _predict_with_thresholds(proba, labels, thresholds)
        cost = _clinical_cost(y_true, pred, labels)
        f1 = f1_score(y_true, pred, average="weighted", zero_division=0)
        if cost < best_cost or (cost == best_cost and f1 > best_f1):
            best_cost = cost
            best_f1 = f1
            best_thresholds = thresholds.copy()

    # Refine with local search
    for _ in range(20):
        delta = np.random.uniform(-0.05, 0.05, n_classes)
        thresholds = np.clip(best_thresholds + delta, 0.1, 0.6)
        pred = _predict_with_thresholds(proba, labels, thresholds)
        cost = _clinical_cost(y_true, pred, labels)
        f1 = f1_score(y_true, pred, average="weighted", zero_division=0)
        if cost < best_cost:
            best_cost = cost
            best_f1 = f1
            best_thresholds = thresholds

    logger.info("Threshold optimization: cost=%.4f, F1=%.4f", best_cost, best_f1)
    return best_thresholds, best_cost, best_f1


class ThresholdOptimizedClassifier:
    """Wrapper that applies optimized thresholds to predict_proba for predictions."""

    def __init__(self, estimator: Any, thresholds: np.ndarray, labels: List[str]):
        self.estimator = estimator
        self.thresholds = np.asarray(thresholds)
        self.labels = list(labels)
        self.classes_ = np.array(labels)

    def get_params(self, deep: bool = True) -> dict:
        """Sklearn-compatible get_params for cloning."""
        return {
            "estimator": self.estimator,
            "thresholds": self.thresholds,
            "labels": self.labels,
        }

    def set_params(self, **params) -> "ThresholdOptimizedClassifier":
        """Sklearn-compatible set_params."""
        if "estimator" in params:
            self.estimator = params["estimator"]
        if "thresholds" in params:
            self.thresholds = params["thresholds"]
        if "labels" in params:
            self.labels = params["labels"]
            self.classes_ = np.array(self.labels)
        return self

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs) -> "ThresholdOptimizedClassifier":
        """Forward fit to inner estimator (for StackingClassifier compatibility)."""
        self.estimator.fit(X, y, **kwargs)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        proba = self.estimator.predict_proba(X)
        pred = _predict_with_thresholds(proba, self.labels, self.thresholds)
        return np.array(pred)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict_proba(X)
