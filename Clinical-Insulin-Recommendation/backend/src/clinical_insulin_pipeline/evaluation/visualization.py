"""Plots: residuals, feature importance, learning curves."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import learning_curve


def plot_residuals(y_true: np.ndarray, y_pred: np.ndarray, out_path: Path, title: str) -> None:
    res = y_true - y_pred
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].scatter(y_pred, res, alpha=0.35, s=8)
    axes[0].axhline(0, color="k", lw=0.8)
    axes[0].set_xlabel("Predicted dose")
    axes[0].set_ylabel("Residual (true − pred)")
    axes[0].set_title(title)
    axes[1].hist(res, bins=40, edgecolor="black", alpha=0.7)
    axes[1].set_xlabel("Residual")
    axes[1].set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_feature_importance(
    names: List[str],
    values: np.ndarray,
    out_path: Path,
    title: str,
    top_k: int = 20,
) -> None:
    order = np.argsort(np.abs(values))[::-1][:top_k]
    fig, ax = plt.subplots(figsize=(8, max(4, top_k * 0.2)))
    ax.barh([names[i] for i in order[::-1]], values[order[::-1]])
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_learning_curve_estimator(
    estimator: Any,
    X: np.ndarray,
    y: np.ndarray,
    out_path: Path,
    title: str,
    cv: int = 5,
) -> None:
    train_sizes, train_scores, val_scores = learning_curve(
        estimator,
        X,
        y,
        cv=cv,
        scoring="neg_root_mean_squared_error",
        train_sizes=np.linspace(0.1, 1.0, 5),
        n_jobs=-1,
    )
    train_rmse = np.sqrt(-train_scores)
    val_rmse = np.sqrt(-val_scores)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(train_sizes, train_rmse.mean(axis=1), label="Train RMSE")
    ax.plot(train_sizes, val_rmse.mean(axis=1), label="Val RMSE")
    ax.fill_between(
        train_sizes,
        val_rmse.mean(axis=1) - val_rmse.std(axis=1),
        val_rmse.mean(axis=1) + val_rmse.std(axis=1),
        alpha=0.2,
    )
    ax.set_xlabel("Training examples")
    ax.set_ylabel("RMSE (IU)")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
