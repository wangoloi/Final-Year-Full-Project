"""
Model evaluation: metrics and comparison across models.
"""

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


def _compute_clinical_cost(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: List[str],
    cost_matrix: Optional[Dict[str, Dict[str, float]]] = None,
) -> float:
    """Compute expected clinical cost from cost matrix. Lower is better."""
    if cost_matrix is None:
        try:
            from ..config.schema import CLINICAL_COST_MATRIX
            cost_matrix = CLINICAL_COST_MATRIX
        except ImportError:
            return float("nan")
    total = 0.0
    n = len(y_true)
    if n == 0 or not labels:
        return float("nan")
    label_list = list(labels)
    for i in range(n):
        t, p = y_true[i], y_pred[i]
        true_s = label_list[int(t)] if np.issubdtype(type(t), np.integer) or isinstance(t, (int, np.integer)) else str(t)
        pred_s = label_list[int(p)] if np.issubdtype(type(p), np.integer) or isinstance(p, (int, np.integer)) else str(p)
        true_s = str(true_s).lower()
        pred_s = str(pred_s).lower()
        row = cost_matrix.get(true_s, {})
        total += row.get(pred_s, 1.0)
    return total / n


def _safe_roc_auc(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    class_order: np.ndarray,
) -> float:
    """Compute ROC-AUC (ovr, weighted). y_true can be labels; class_order matches proba columns."""
    try:
        from sklearn.metrics import roc_auc_score
        label_to_idx = {c: i for i, c in enumerate(class_order)}
        y_idx = np.array([label_to_idx.get(y, 0) for y in y_true])
        return float(roc_auc_score(y_idx, y_proba, multi_class="ovr", average="weighted"))
    except Exception:
        return float("nan")


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
    clinical_cost: float = float("nan")  # Expected cost from clinical cost matrix
    classification_report_str: Optional[str] = None


def evaluate_model(
    estimator: Any,
    X: np.ndarray,
    y_true: np.ndarray,
    model_name: str = "model",
    labels: Optional[List[str]] = None,
    compute_clinical_cost: bool = True,
) -> EvaluationResult:
    """
    Compute accuracy, precision, recall, F1 (macro/weighted), ROC-AUC (ovr), confusion matrix.
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
    clinical_cost = float("nan")
    if compute_clinical_cost:
        try:
            clinical_cost = _compute_clinical_cost(y_true, y_pred, labels)
        except Exception:
            pass
    report_str = classification_report(y_true, y_pred, labels=labels, zero_division=0)
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
    )


def compare_models(
    training_results: List[Any],
    X_test: np.ndarray,
    y_test: np.ndarray,
    labels: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Evaluate each trained model on test set and return a comparison DataFrame.
    training_results: list of TrainingResult from ModelTrainer.train_all().
    """
    if labels is None:
        labels = list(np.unique(y_test))
    rows = []
    for res in training_results:
        ev = evaluate_model(
            res.best_estimator,
            X_test,
            y_test,
            model_name=res.model_name,
            labels=labels,
        )
        rows.append({
            "model": ev.model_name,
            "accuracy": ev.accuracy,
            "precision_weighted": ev.precision_weighted,
            "recall_weighted": ev.recall_weighted,
            "f1_weighted": ev.f1_weighted,
            "f1_macro": ev.f1_macro,
            "roc_auc_weighted": ev.roc_auc_ovr_weighted,
            "clinical_cost": ev.clinical_cost,
        })
    return pd.DataFrame(rows)


def format_confusion_matrix(cm: np.ndarray, labels: List[str]) -> str:
    """Return a readable string of the confusion matrix."""
    df = pd.DataFrame(cm, index=labels, columns=labels)
    return df.to_string()
