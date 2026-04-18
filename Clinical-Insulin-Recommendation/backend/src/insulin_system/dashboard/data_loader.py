"""
Dashboard data loader: cached bundle, evaluation artifacts, recommendations, reference data.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..config.schema import DashboardConfig, DataSchema, PipelineConfig
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
    reference_df: Optional[pd.DataFrame] = None  # raw test rows for profile
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
    """
    Load all dashboard data. If data_path is set and run_pipeline_for_reference,
    runs pipeline once to get reference X/y and raw test df (for patient profiles).
    """
    cfg = config or DashboardConfig()
    out = DashboardData()

    bundle, meta = _load_bundle_safe(cfg.best_model_dir)
    out.bundle = bundle
    out.metadata = meta
    if bundle:
        out.feature_names = list(bundle.feature_names)
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

    if not run_pipeline_for_reference or not data_path or not Path(data_path).exists():
        return out
    if not bundle:
        return out
    # Load reference data via pipeline (raw test for profile + X_test, y_test for similar)
    try:
        from ..data_processing.load import DataLoader
        from ..data_processing.split import TemporalSplitter
        schema = DataSchema()
        pipe_cfg = PipelineConfig()
        loader = DataLoader(schema=schema, file_path=data_path)
        raw_df = loader.load_and_validate(Path(data_path))
        splitter = TemporalSplitter(
            schema=schema,
            train_ratio=pipe_cfg.train_ratio,
            val_ratio=pipe_cfg.val_ratio,
            random_state=pipe_cfg.random_state,
        )
        _train, _val, raw_test_df = splitter.split(raw_df, sort_by=schema.PATIENT_ID)
        out.reference_df = raw_test_df
        X_test = bundle.transform(raw_test_df.drop(columns=[schema.TARGET], errors="ignore"))
        out.reference_X = np.asarray(X_test)
        if schema.TARGET in raw_test_df.columns:
            out.reference_y = raw_test_df[schema.TARGET].values
        else:
            out.reference_y = None
    except Exception:
        pass
    return out
