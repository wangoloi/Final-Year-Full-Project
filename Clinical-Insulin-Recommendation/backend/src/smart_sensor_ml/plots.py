"""9. Visualizations — confusion matrix, ROC, importances, distributions."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import ConfusionMatrixDisplay, auc, roc_curve
from sklearn.preprocessing import label_binarize

from smart_sensor_ml import config


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: List[int],
    class_names: List[str],
    out_path: Path,
    title: str = "Confusion matrix",
) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(
        y_true, y_pred, labels=labels, display_labels=class_names, ax=ax, colorbar=True
    )
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_roc_multiclass(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    out_path: Path,
    title: str = "ROC (one-vs-rest)",
) -> None:
    y_bin = label_binarize(y_true, classes=list(range(config.N_CLASSES)))
    fig, ax = plt.subplots(figsize=(7, 6))
    for i in range(config.N_CLASSES):
        if y_bin.shape[1] <= i:
            continue
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, lw=2, label=f"{config.CLASS_NAMES[i]} (AUC = {roc_auc:.2f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_feature_importance(
    importances: np.ndarray,
    names: List[str],
    out_path: Path,
    top_k: int = 15,
    title: str = "Feature importance",
) -> None:
    order = np.argsort(importances)[::-1][:top_k]
    fig, ax = plt.subplots(figsize=(8, max(4, top_k * 0.25)))
    sns.barplot(x=importances[order], y=[names[i] for i in order], ax=ax)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_regression_residuals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    out_path: Path,
    title: str = "Residuals (test)",
) -> None:
    res = y_true - y_pred
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    sns.histplot(res, kde=True, ax=axes[0])
    axes[0].set_title("Residual distribution")
    axes[0].set_xlabel("y_true - y_pred")
    sns.scatterplot(x=y_pred, y=res, alpha=0.2, ax=axes[1])
    axes[1].axhline(0.0, color="k", ls="--")
    axes[1].set_xlabel("Predicted dose")
    axes[1].set_ylabel("Residual")
    axes[1].set_title("Residuals vs predicted")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_pred_vs_actual(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    out_path: Path,
    title: str = "Predicted vs actual (test)",
) -> None:
    lo = float(min(y_true.min(), y_pred.min()))
    hi = float(max(y_true.max(), y_pred.max()))
    fig, ax = plt.subplots(figsize=(6, 6))
    sns.scatterplot(x=y_true, y=y_pred, alpha=0.2, ax=ax)
    ax.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax.set_xlabel("Actual insulin dose")
    ax.set_ylabel("Predicted insulin dose")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_target_and_glucose_distributions(df: pd.DataFrame, out_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    sns.histplot(pd.to_numeric(df[config.COL_TARGET], errors="coerce").dropna(), kde=True, ax=axes[0])
    axes[0].set_title("Insulin_Dose distribution")
    sns.histplot(pd.to_numeric(df["Glucose_Level"], errors="coerce").dropna(), kde=True, ax=axes[1])
    axes[1].set_title("Glucose_Level distribution")
    fig.tight_layout()
    fig.savefig(out_dir / "distributions_glucose_insulin.png", dpi=150)
    plt.close(fig)
