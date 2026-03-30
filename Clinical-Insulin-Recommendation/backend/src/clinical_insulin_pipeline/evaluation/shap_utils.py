"""SHAP force-style explanation for a single sample (tree models preferred)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

import numpy as np

try:
    import shap
except ImportError:  # pragma: no cover
    shap = None


def try_shap_force_plot(
    model: Any,
    X_background: np.ndarray,
    x_single: np.ndarray,
    feature_names: List[str],
    out_path: Path,
) -> bool:
    """
    Save SHAP force plot for one row. Returns False if not available.
    Uses TreeExplainer when possible.
    """
    if shap is None:
        return False
    x_single = np.asarray(x_single, dtype=float).reshape(1, -1)
    X_background = np.asarray(X_background, dtype=float)
    if X_background.shape[0] > 200:
        rng = np.random.default_rng(42)
        idx = rng.choice(X_background.shape[0], size=200, replace=False)
        X_background = X_background[idx]

    try:
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(x_single)
        expected = explainer.expected_value
        if isinstance(sv, list):
            sv = sv[0]
        sv = np.asarray(sv).reshape(-1)
        exp_val = float(expected[0]) if hasattr(expected, "__len__") else float(expected)
    except Exception:
        try:
            explainer = shap.KernelExplainer(model.predict, X_background[:50])
            sv = explainer.shap_values(x_single, nsamples=100)[0]
            exp_val = float(explainer.expected_value)
        except Exception:
            return False

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 4))
    order = np.argsort(np.abs(sv))[::-1][:15]
    ax.barh([feature_names[i] for i in order[::-1]], sv[order[::-1]])
    ax.axvline(0, color="k", lw=0.6)
    ax.set_title(f"SHAP values (base ≈ {exp_val:.2f})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return True
