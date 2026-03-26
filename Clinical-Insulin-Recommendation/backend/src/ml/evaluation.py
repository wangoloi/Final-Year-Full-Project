"""
Comprehensive model evaluation: metrics, classification report, CV, and cost analysis.

Provides weighted F1, per-class precision/recall, confusion matrix, and clinical cost.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    precision_recall_fscore_support,
)
from sklearn.model_selection import cross_validate, StratifiedKFold

logger = logging.getLogger(__name__)

# Clinical cost: cost[true][pred] = penalty
CLINICAL_COST_MATRIX = {
    "down": {"down": 0, "up": 5, "steady": 1, "no": 1},
    "up": {"down": 5, "up": 0, "steady": 1, "no": 1},
    "steady": {"down": 2, "up": 2, "steady": 0, "no": 0.5},
    "no": {"down": 3, "up": 2, "steady": 0.5, "no": 0},
}


@dataclass
class EvaluationResult:
    """Evaluation metrics for one model on one dataset."""

    model_name: str
    accuracy: float
    precision_weighted: float
    recall_weighted: float
    f1_weighted: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    roc_auc_ovr_weighted: float
    confusion_matrix: np.ndarray
    labels: Optional[List[str]] = None
    clinical_cost: float = float("nan")
    classification_report_str: Optional[str] = None
    per_class_metrics: Optional[List[Dict]] = None


def _compute_clinical_cost(y_true: np.ndarray, y_pred: np.ndarray, labels: List[str]) -> float:
    """Average clinical cost from cost matrix."""
    total, n = 0.0, len(y_true)
    if n == 0 or not labels:
        return float("nan")
    label_list = list(labels)
    for i in range(n):
        t, p = str(y_true[i]).lower(), str(y_pred[i]).lower()
        if t in CLINICAL_COST_MATRIX and p in CLINICAL_COST_MATRIX[t]:
            total += CLINICAL_COST_MATRIX[t][p]
        else:
            total += 1.0
    return total / n


def _safe_roc_auc(y_true: np.ndarray, y_proba: np.ndarray, class_order: np.ndarray) -> float:
    """ROC-AUC One-vs-Rest weighted."""
    try:
        from sklearn.metrics import roc_auc_score
        label_to_idx = {c: i for i, c in enumerate(class_order)}
        y_idx = np.array([label_to_idx.get(str(y).lower(), 0) for y in y_true])
        return float(roc_auc_score(y_idx, y_proba, multi_class="ovr", average="weighted"))
    except Exception:
        return float("nan")


def evaluate_model(
    estimator: Any,
    X: np.ndarray,
    y_true: np.ndarray,
    model_name: str = "model",
    labels: Optional[List[str]] = None,
    compute_clinical_cost: bool = True,
    include_classification_report: bool = True,
) -> EvaluationResult:
    """
    Compute comprehensive metrics: accuracy, precision/recall/F1 (macro+weighted),
    ROC-AUC, confusion matrix, classification report, per-class metrics, clinical cost.
    """
    y_pred = estimator.predict(X)
    if labels is None:
        labels = list(np.unique(y_true))

    acc = float(accuracy_score(y_true, y_pred))
    pw = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
    rw = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
    f1w = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    pm = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    rm = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1m = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    roc_auc = float("nan")
    if hasattr(estimator, "predict_proba"):
        try:
            y_proba = estimator.predict_proba(X)
            classes_ = getattr(estimator, "classes_", None)
            if classes_ is None and hasattr(estimator, "named_steps"):
                classes_ = getattr(estimator.named_steps.get("clf"), "classes_", labels)
            class_order = np.array(classes_) if classes_ is not None else np.array(labels)
            roc_auc = _safe_roc_auc(y_true, y_proba, class_order)
        except Exception:
            pass

    clinical_cost = _compute_clinical_cost(y_true, y_pred, labels) if compute_clinical_cost else float("nan")

    report_str = None
    per_class = None
    if include_classification_report:
        report_str = classification_report(y_true, y_pred, labels=labels, zero_division=0)
        p_per, r_per, f_per, _ = precision_recall_fscore_support(
            y_true, y_pred, labels=labels, zero_division=0
        )
        per_class = [
            {"class": labels[i], "precision": float(p_per[i]), "recall": float(r_per[i]), "f1": float(f_per[i])}
            for i in range(len(labels))
        ]

    return EvaluationResult(
        model_name=model_name,
        accuracy=acc,
        precision_weighted=pw,
        recall_weighted=rw,
        f1_weighted=f1w,
        precision_macro=pm,
        recall_macro=rm,
        f1_macro=f1m,
        roc_auc_ovr_weighted=roc_auc,
        confusion_matrix=cm,
        labels=labels,
        clinical_cost=clinical_cost,
        classification_report_str=report_str,
        per_class_metrics=per_class,
    )


def cross_validate_model(
    estimator: Any,
    X: np.ndarray,
    y: np.ndarray,
    cv: int = 5,
    scoring: str = "f1_weighted",
    random_state: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Run stratified cross-validation and return scores.

    Returns dict with keys: test_f1_weighted, test_accuracy, etc.
    """
    cv_splitter = StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)
    scores = cross_validate(
        estimator, X, y,
        cv=cv_splitter,
        scoring=scoring,
        return_train_score=True,
        n_jobs=1,
    )
    return scores
