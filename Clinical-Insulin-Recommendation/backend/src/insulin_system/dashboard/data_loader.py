"""
Dashboard data loader: evaluation artifacts and recommendations from disk (no training pipeline).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..config.schema import DashboardConfig
from ..persistence import load_best_model, InferenceBundle


@dataclass
class DashboardData:
    """Cached data for the dashboard: bundle, evaluation summary, recommendations, reference."""

    bundle: Optional[InferenceBundle] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    evaluation_summary: Optional[pd.DataFrame] = None
    temporal_validation: Optional[pd.DataFrame] = None
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    reference_X: Optional[np.ndarray] = None
    reference_y: Optional[np.ndarray] = None
    reference_df: Optional[pd.DataFrame] = None
    feature_names: List[str] = field(default_factory=list)
    model_name: str = ""
    classes: List[str] = field(default_factory=list)
    explainability_paths: Dict[str, str] = field(default_factory=dict)


def _load_bundle_safe(model_dir: Path) -> Tuple[Optional[InferenceBundle], Dict[str, Any]]:
    try:
        bundle = load_best_model(model_dir)
        meta_path = model_dir / "metadata.json"
        meta = {}
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        return bundle, meta
    except Exception:
        return None, {}


def _load_evaluation_summary(eval_dir: Path) -> Optional[pd.DataFrame]:
    path = eval_dir / "evaluation_summary.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


def _load_temporal_validation(eval_dir: Path, model_name: str) -> Optional[pd.DataFrame]:
    path = eval_dir / model_name / "temporal_validation.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


def _load_recommendations(rec_dir: Path) -> List[Dict[str, Any]]:
    path = rec_dir / "recommendations.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def load_dashboard_data(
    config: Optional[DashboardConfig] = None,
    data_path: Optional[Path] = None,
    run_pipeline_for_reference: bool = True,
) -> DashboardData:
    """Load dashboard artifacts from configured output dirs. No offline pipeline runs."""
    cfg = config or DashboardConfig()
    out = DashboardData()

    bundle, meta = _load_bundle_safe(cfg.best_model_dir)
    out.bundle = bundle
    out.metadata = meta
    if bundle:
        out.feature_names = list(getattr(bundle, "feature_names", []) or [])
        out.model_name = getattr(bundle, "model_name", meta.get("model_name", ""))
        out.classes = list(meta.get("classes", []) or getattr(bundle, "classes_", []))

    out.evaluation_summary = _load_evaluation_summary(cfg.evaluation_dir)
    if out.model_name:
        out.temporal_validation = _load_temporal_validation(cfg.evaluation_dir, out.model_name)
    out.recommendations = _load_recommendations(cfg.recommendations_dir)

    explain_dir = cfg.explainability_dir / out.model_name if out.model_name else Path()
    if explain_dir.exists():
        for f in explain_dir.glob("*.png"):
            out.explainability_paths[f.stem] = str(f)
        for f in explain_dir.glob("*.html"):
            out.explainability_paths[f.stem] = str(f)
        rec_dir = explain_dir / "clinical_reports"
        if rec_dir.exists():
            for f in rec_dir.glob("patient_*.md"):
                out.explainability_paths[f.stem] = str(f)

    return out
