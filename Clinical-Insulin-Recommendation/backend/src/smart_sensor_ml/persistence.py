"""10. Save / load deployment bundle (joblib)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import joblib
import numpy as np
from smart_sensor_ml import config
from smart_sensor_ml.predict import predict_with_explanation
from smart_sensor_ml.preprocess import PreprocessPipeline
from smart_sensor_ml.recommend import recommend
from smart_sensor_ml.inference import measurement_time_category

logger = logging.getLogger(__name__)


@dataclass
class ProductionBundle:
    """Everything needed for consistent train → inference (§11: model + preprocessor + metadata)."""

    model: Any
    model_name: str
    preprocessor: PreprocessPipeline
    class_names: List[str] = field(default_factory=lambda: list(config.CLASS_NAMES))
    """Tier names for display; primary prediction is continuous dose (regression)."""
    feature_names: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Includes numeric_defaults (per-column medians from training) for filling missing sensor fields at inference."""

    def __post_init__(self) -> None:
        if not self.feature_names:
            self.feature_names = list(self.preprocessor.selected_features)


def save_model(bundle: ProductionBundle, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out_dir / "bundle.joblib")
    meta = {
        "model_name": bundle.model_name,
        "class_names": bundle.class_names,
        "feature_names": bundle.feature_names,
        **bundle.metadata,
    }
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved bundle to %s", out_dir)


def load_model(out_dir: Path) -> ProductionBundle:
    path = Path(out_dir) / "bundle.joblib"
    if not path.is_file():
        raise FileNotFoundError(f"No bundle at {path}")
    b = joblib.load(path)
    if not isinstance(b, ProductionBundle):
        raise TypeError("Invalid bundle format")
    return b


def predict_new_data(
    bundle: ProductionBundle,
    row: Mapping[str, Any],
    with_recommendation: bool = True,
) -> Dict[str, Any]:
    """
    Apply the same preprocessor + model as training.

    `row` must include measurement_time, meal_context, activity_context, Patient_ID, Timestamp,
    and sensor numeric columns (missing values filled from bundle.metadata[\"numeric_defaults\"]).
    """
    imp = None
    if hasattr(bundle.model, "feature_importances_"):
        imp = np.asarray(bundle.model.feature_importances_)
    meta = bundle.metadata or {}
    pred = predict_with_explanation(
        bundle.model,
        bundle.preprocessor,
        row,
        feature_importance=imp,
        feature_names=bundle.feature_names,
        insulin_bin_edges=meta.get("insulin_bin_edges"),
        train_insulin_mean=meta.get("train_insulin_mean"),
        train_insulin_std=meta.get("train_insulin_std"),
    )
    if with_recommendation:
        g = row.get("Glucose_Level")
        pred["recommendation"] = recommend(
            pred["predicted_tier_name"],
            glucose_level=float(g) if g is not None else None,
            time_category=measurement_time_category(row.get(config.COL_MEASUREMENT_TIME)),
            meal_context=row.get(config.COL_MEAL_CONTEXT),
            activity_context=row.get(config.COL_ACTIVITY_CONTEXT),
        )
    return pred
