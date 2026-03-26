"""
ML visualization: confusion matrix, ROC, feature importance, learning curve,
class distribution, model comparison.

Uses consistent styling and saves to organized output folders.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

# Consistent styling
FIGURE_STYLE = {
    "figure.figsize": (8, 6),
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
}
COLORS = ["#2ecc71", "#3498db", "#e74c3c", "#9b59b6", "#f39c12"]


def _setup_style():
    """Apply consistent figure style."""
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        try:
            plt.style.use("seaborn-whitegrid")
        except OSError:
            pass
    for k, v in FIGURE_STYLE.items():
        plt.rcParams[k] = v


def plot_confusion_matrix(
    cm: np.ndarray,
    labels: List[str],
    output_path: Path,
    title: str = "Confusion Matrix (Test)",
    cmap: str = "Blues",
) -> Path:
    """Plot confusion matrix with annotations and labels."""
    _setup_style()
    fig, ax = plt.subplots(figsize=(7, 6))
    df_cm = pd.DataFrame(cm, index=labels, columns=labels)
    sns.heatmap(df_cm, annot=True, fmt="d", cmap=cmap, ax=ax, cbar_kws={"label": "Count"})
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("True Label")
    ax.set_xlabel("Predicted Label")
    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def plot_roc_curves(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    classes: np.ndarray,
    output_path: Path,
    title: str = "ROC Curves (One-vs-Rest)",
) -> Path:
    """Plot ROC curves for each class."""
    from sklearn.metrics import roc_curve, auc

    _setup_style()
    fig, ax = plt.subplots(figsize=(8, 6))
    label_to_idx = {c: i for i, c in enumerate(classes)}
    y_bin = np.zeros((len(y_true), len(classes)))
    for i, y in enumerate(y_true):
        idx = label_to_idx.get(str(y).lower(), 0)
        y_bin[i, idx] = 1

    for i, c in enumerate(classes):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, label=f"{c} (AUC={roc_auc:.3f})", linewidth=2)

    ax.plot([0, 1], [0, 1], "k--", linewidth=1, alpha=0.5)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def plot_feature_importance(
    importance: np.ndarray,
    feature_names: List[str],
    output_path: Path,
    title: str = "Feature Importance (Top 20)",
    top_k: int = 20,
) -> Path:
    """Plot horizontal bar chart of feature importance."""
    _setup_style()
    idx = np.argsort(importance)[::-1][:top_k]
    imp = importance[idx]
    names = [feature_names[i] for i in idx]
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(names)))
    ax.barh(range(len(names)), imp, color=colors)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Importance")
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def plot_learning_curve(
    train_sizes: np.ndarray,
    train_scores_mean: np.ndarray,
    train_scores_std: np.ndarray,
    val_scores_mean: np.ndarray,
    val_scores_std: np.ndarray,
    output_path: Path,
    scoring_name: str = "F1 Weighted",
) -> Path:
    """Plot learning curve with train and validation scores."""
    _setup_style()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.fill_between(train_sizes, train_scores_mean - train_scores_std, train_scores_mean + train_scores_std, alpha=0.2)
    ax.fill_between(train_sizes, val_scores_mean - val_scores_std, val_scores_mean + val_scores_std, alpha=0.2)
    ax.plot(train_sizes, train_scores_mean, "o-", label="Train", linewidth=2)
    ax.plot(train_sizes, val_scores_mean, "o-", label="Cross-Validation", linewidth=2)
    ax.set_title("Learning Curve", fontsize=14, fontweight="bold")
    ax.set_xlabel("Training Examples")
    ax.set_ylabel(scoring_name)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def plot_class_distribution(
    y: np.ndarray,
    output_path: Path,
    title: str = "Class Distribution",
) -> Path:
    """Plot bar chart of class distribution."""
    _setup_style()
    unique, counts = np.unique(y, return_counts=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = plt.cm.Set3(np.linspace(0, 1, len(unique)))
    ax.bar(unique.astype(str), counts, color=colors)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Class")
    ax.set_ylabel("Count")
    for i, (u, c) in enumerate(zip(unique, counts)):
        ax.text(i, c + max(counts) * 0.01, str(c), ha="center", fontsize=10)
    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def plot_model_comparison(
    summary_df: pd.DataFrame,
    output_path: Path,
    metrics: List[str] = ("f1_weighted", "accuracy", "roc_auc_weighted"),
) -> Path:
    """Plot model comparison bar chart."""
    _setup_style()
    df = summary_df.set_index("model")[metrics]
    fig, ax = plt.subplots(figsize=(10, 5))
    df.plot(kind="bar", ax=ax, width=0.8, colormap="viridis")
    ax.set_title("Model Comparison", fontsize=14, fontweight="bold")
    ax.set_xlabel("Model")
    ax.set_ylabel("Score")
    ax.legend(title="Metric")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path
