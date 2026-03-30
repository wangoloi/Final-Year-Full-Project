"""
SHAP background data loader.

Single responsibility: load and cache background X for SHAP explainer.
"""
from typing import Any, Optional

import numpy as np

from ...config.schema import DashboardConfig
from .route_data import RANDOM_SEED, SHAP_BACKGROUND_SAMPLE_SIZE

_background_X: Optional[Any] = None


def load_background_if_needed() -> Optional[Any]:
    """Load SHAP background sample from reference data. Returns cached or None."""
    global _background_X
    if _background_X is not None:
        return _background_X

    try:
        from ...dashboard.data_loader import load_dashboard_data
        cfg = DashboardConfig()
        data = load_dashboard_data(cfg, cfg.data_path, run_pipeline_for_reference=True)
        if data.reference_X is None or data.reference_X.shape[0] == 0:
            _background_X = None
            return None

        n = min(SHAP_BACKGROUND_SAMPLE_SIZE, data.reference_X.shape[0])
        rng = np.random.default_rng(RANDOM_SEED)
        idx = rng.choice(data.reference_X.shape[0], size=n, replace=False)
        _background_X = data.reference_X[idx]
        return _background_X
    except Exception:
        _background_X = None
        return None
