"""6–10. Evaluation — metrics, CV, composite model selection."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def composite_score(
    f1_weighted: float,
    roc_auc_ovr: float,
    accuracy: float,
    precision_weighted: float,
    recall_weighted: float,
) -> float:
    """Weighted combination: F1, ROC, Accuracy, Precision, Recall (NaN ROC → 0)."""
    roc = 0.0 if roc_auc_ovr != roc_auc_ovr or roc_auc_ovr is None else float(roc_auc_ovr)
    return (
        0.30 * float(f1_weighted)
        + 0.25 * roc
        + 0.20 * float(accuracy)
        + 0.15 * float(precision_weighted)
        + 0.10 * float(recall_weighted)
    )


@dataclass
class EvalResult:
    model_name: str
    accuracy: float
    precision_macro: float
    precision_weighted: float
    recall_macro: float
    recall_weighted: float
    f1_macro: float
    f1_weighted: float
    roc_auc_ovr: float
    composite_score: float
    confusion_matrix: np.ndarray
    report: str
    train_accuracy: float = float("nan")
    overfit_gap: float = float("nan")


def evaluate_model(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model_name: str = "model",
    labels: Optional[List[int]] = None,
    X_train: Optional[np.ndarray] = None,
    y_train: Optional[np.ndarray] = None,
) -> EvalResult:
    labels = labels or list(range(config.N_CLASSES))
    y_pred = model.predict(X_test)
    proba = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_test)
    acc = accuracy_score(y_test, y_pred)
    prec_m = precision_score(y_test, y_pred, average="macro", zero_division=0, labels=labels)
    prec_w = precision_score(y_test, y_pred, average="weighted", zero_division=0, labels=labels)
    rec_m = recall_score(y_test, y_pred, average="macro", zero_division=0, labels=labels)
    rec_w = recall_score(y_test, y_pred, average="weighted", zero_division=0, labels=labels)
    f1m = f1_score(y_test, y_pred, average="macro", zero_division=0, labels=labels)
    f1w = f1_score(y_test, y_pred, average="weighted", zero_division=0, labels=labels)
    roc = float("nan")
    if proba is not None and len(np.unique(y_test)) >= 2:
        try:
            roc = roc_auc_score(y_test, proba, multi_class="ovr", average="weighted", labels=labels)
        except Exception:
            pass
    comp = composite_score(f1w, roc, acc, prec_w, rec_w)
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    rep = classification_report(y_test, y_pred, labels=labels, target_names=list(config.CLASS_NAMES), zero_division=0)
    train_acc = float("nan")
    gap = float("nan")
    if X_train is not None and y_train is not None:
        train_acc = float(accuracy_score(y_train, model.predict(X_train)))
        gap = float(train_acc - acc)
    return EvalResult(
        model_name=model_name,
        accuracy=float(acc),
        precision_macro=float(prec_m),
        precision_weighted=float(prec_w),
        recall_macro=float(rec_m),
        recall_weighted=float(rec_w),
        f1_macro=float(f1m),
        f1_weighted=float(f1w),
        roc_auc_ovr=float(roc) if roc == roc else float("nan"),
        composite_score=float(comp),
        confusion_matrix=cm,
        report=rep,
        train_accuracy=train_acc,
        overfit_gap=gap,
    )


def cross_validate_groups(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    n_splits: int = 5,
    random_state: int = 42,
) -> Dict[str, float]:
    """StratifiedGroupKFold — grouped patient splits (§8)."""
    n_splits = min(n_splits, len(np.unique(groups)))
    if n_splits < 2:
        return {}
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    accs, f1ws, rocs, comps = [], [], [], []
    for train_idx, val_idx in cv.split(X, y, groups):
        m = _clone_and_fit(model, X[train_idx], y[train_idx])
        y_p = m.predict(X[val_idx])
        y_v = y[val_idx]
        accs.append(accuracy_score(y_v, y_p))
        f1ws.append(f1_score(y_v, y_p, average="weighted", zero_division=0))
        roc_fold = float("nan")
        if hasattr(m, "predict_proba"):
            try:
                proba = m.predict_proba(X[val_idx])
                roc_fold = roc_auc_score(
                    y_v, proba, multi_class="ovr", average="weighted", labels=list(range(config.N_CLASSES))
                )
                rocs.append(roc_fold)
            except Exception:
                pass
        prec_w = precision_score(y_v, y_p, average="weighted", zero_division=0)
        rec_w = recall_score(y_v, y_p, average="weighted", zero_division=0)
        f1w = f1_score(y_v, y_p, average="weighted", zero_division=0)
        comps.append(composite_score(f1w, roc_fold, float(accs[-1]), prec_w, rec_w))

    out: Dict[str, float] = {
        "cv_accuracy_mean": float(np.mean(accs)),
        "cv_accuracy_std": float(np.std(accs)),
        "cv_f1_weighted_mean": float(np.mean(f1ws)),
        "cv_f1_weighted_std": float(np.std(f1ws)),
        "cv_composite_mean": float(np.mean(comps)),
        "cv_composite_std": float(np.std(comps)),
    }
    if rocs:
        out["cv_roc_auc_mean"] = float(np.mean(rocs))
        out["cv_roc_auc_std"] = float(np.std(rocs))
    return out


def _clone_and_fit(model: Any, X: np.ndarray, y: np.ndarray) -> Any:
    from sklearn.base import clone

    m = clone(model)
    m.fit(X, y)
    return m


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


@dataclass
class EvalResultRegression:
    model_name: str
    r2: float
    rmse: float
    mae: float
    train_r2: float = float("nan")
    train_rmse: float = float("nan")
    overfit_gap_r2: float = float("nan")
    overfit_gap_rmse: float = float("nan")


def evaluate_regression_model(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    model_name: str = "model",
    X_train: Optional[np.ndarray] = None,
    y_train: Optional[np.ndarray] = None,
) -> EvalResultRegression:
    y_pred = model.predict(X)
    r2 = float(r2_score(y, y_pred))
    rmse = _rmse(y, y_pred)
    mae = float(mean_absolute_error(y, y_pred))
    tr_r2 = float("nan")
    tr_rmse = float("nan")
    gap_r2 = float("nan")
    gap_rmse = float("nan")
    if X_train is not None and y_train is not None:
        y_tr_p = model.predict(X_train)
        tr_r2 = float(r2_score(y_train, y_tr_p))
        tr_rmse = _rmse(y_train, y_tr_p)
        gap_r2 = float(tr_r2 - r2)
        gap_rmse = float(tr_rmse - rmse)
    return EvalResultRegression(
        model_name=model_name,
        r2=r2,
        rmse=rmse,
        mae=mae,
        train_r2=tr_r2,
        train_rmse=tr_rmse,
        overfit_gap_r2=gap_r2,
        overfit_gap_rmse=gap_rmse,
    )


def cross_validate_groups_regression(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    n_splits: int = 5,
    random_state: int = 42,
) -> Dict[str, float]:
    """GroupKFold on patients — regression metrics (R², RMSE)."""
    n_splits = min(n_splits, len(np.unique(groups)))
    if n_splits < 2:
        return {}
    cv = GroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    r2s, rmses = [], []
    for train_idx, val_idx in cv.split(X, y, groups):
        m = _clone_and_fit(model, X[train_idx], y[train_idx])
        y_p = m.predict(X[val_idx])
        y_v = y[val_idx]
        r2s.append(r2_score(y_v, y_p))
        rmses.append(_rmse(y_v, y_p))
    return {
        "cv_r2_mean": float(np.mean(r2s)),
        "cv_r2_std": float(np.std(r2s)),
        "cv_rmse_mean": float(np.mean(rmses)),
        "cv_rmse_std": float(np.std(rmses)),
    }


def comparison_table(results: List[EvalResult]) -> pd.DataFrame:
    """Rank by composite_score, then hold-out F1 weighted."""
    rows = []
    for r in results:
        rows.append(
            {
                "model": r.model_name,
                "accuracy": r.accuracy,
                "precision_macro": r.precision_macro,
                "precision_weighted": r.precision_weighted,
                "recall_macro": r.recall_macro,
                "recall_weighted": r.recall_weighted,
                "f1_macro": r.f1_macro,
                "f1_weighted": r.f1_weighted,
                "roc_auc_ovr": r.roc_auc_ovr,
                "composite_score": r.composite_score,
                "train_accuracy": r.train_accuracy,
                "overfit_gap": r.overfit_gap,
            }
        )
    df = pd.DataFrame(rows)
    return df.sort_values(["composite_score", "f1_weighted"], ascending=False).reset_index(drop=True)
