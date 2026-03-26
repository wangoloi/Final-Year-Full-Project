"""
Smart Sensor ML (ProductionBundle) integration for FastAPI.

Loads the Smart Sensor bundle (default ``outputs/smart_sensor_ml/model_bundle``,
or ``SMART_SENSOR_BUNDLE_DIR``) and maps requests to CSV-shaped rows.
"""
from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import numpy as np

from ..config.schema import DashboardConfig, get_glucose_zone, get_glucose_zone_cds
from .schemas import ExplanationDriver, FeatureImportanceResponse, PredictionResponse, RecommendationResponse
from .recommend_response_builder import build_response

logger = logging.getLogger(__name__)

_bundle_cache = None
_bundle_path_resolved: Optional[Path] = None


def smart_sensor_bundle_path(cfg: Optional[DashboardConfig] = None) -> Path:
    cfg = cfg or DashboardConfig()
    return Path(cfg.smart_sensor_bundle_dir).resolve()


def smart_sensor_bundle_available() -> bool:
    p = smart_sensor_bundle_path() / "bundle.joblib"
    return p.is_file()


def get_smart_sensor_feature_importance() -> Optional[FeatureImportanceResponse]:
    """
    Feature importance from the Smart Sensor model (tree importances or linear |coef|),
    aligned to ``bundle.feature_names``. Same semantics as legacy GET /feature-importance.
    """
    bundle = load_smart_sensor_bundle()
    est = bundle.model
    if hasattr(est, "named_steps") and "clf" in getattr(est, "named_steps", {}):
        est = est.named_steps["clf"]
    names = list(bundle.feature_names)
    importance = None
    if hasattr(est, "feature_importances_"):
        importance = np.asarray(est.feature_importances_).ravel().tolist()
    elif hasattr(est, "coef_"):
        coef = np.asarray(est.coef_)
        importance = np.mean(np.abs(coef), axis=0).tolist()
    if importance is not None and len(importance) == len(names):
        return FeatureImportanceResponse(
            feature_names=names,
            importance=importance,
            source="builtin",
        )
    return None


def load_smart_sensor_bundle():
    global _bundle_cache, _bundle_path_resolved
    from smart_sensor_ml.persistence import ProductionBundle, load_model

    p = smart_sensor_bundle_path()
    if _bundle_cache is not None and _bundle_path_resolved == p:
        return _bundle_cache
    b = load_model(p)
    if not isinstance(b, ProductionBundle):
        raise TypeError("Invalid smart sensor bundle")
    _bundle_cache = b
    _bundle_path_resolved = p
    logger.info("Loaded Smart Sensor bundle: %s", b.model_name)
    return b


def run_smart_sensor_predict(body: Dict[str, Any]) -> PredictionResponse:
    from smart_sensor_ml.inference import build_inference_row
    from smart_sensor_ml.persistence import predict_new_data

    bundle = load_smart_sensor_bundle()
    defaults = bundle.metadata.get("numeric_defaults") or {}
    row = build_inference_row(body, defaults)
    out = predict_new_data(bundle, row, with_recommendation=False)
    pred_name = out["predicted_tier_name"]
    dose = out.get("predicted_insulin_dose")
    proba = out["class_probabilities"]
    conf = float(proba.get(pred_name, 0.0))
    arr = np.array(list(proba.values()), dtype=float)
    entropy = float(-(arr * np.log(arr + 1e-10)).sum())
    return PredictionResponse(
        predicted_class=pred_name,
        predicted_insulin_units=float(dose) if dose is not None else None,
        confidence=conf,
        uncertainty_entropy=entropy,
        probability_breakdown={str(k): float(v) for k, v in proba.items()},
        feature_names_used=list(bundle.feature_names),
    )


def run_smart_sensor_recommend(body: Dict[str, Any]) -> RecommendationResponse:
    """Full recommendation using Smart Sensor tier model + rule layer + CDS-style wrapper."""
    from smart_sensor_ml.inference import build_inference_row, measurement_time_category
    from smart_sensor_ml.persistence import predict_new_data

    bundle = load_smart_sensor_bundle()
    defaults = bundle.metadata.get("numeric_defaults") or {}
    row = build_inference_row(body, defaults)
    out = predict_new_data(bundle, row, with_recommendation=True)

    pred = out["predicted_tier_name"]
    proba = out["class_probabilities"]
    conf = float(proba.get(pred, 0.0))
    arr = np.array(list(proba.values()), dtype=float)
    entropy = float(-(arr * np.log(arr + 1e-10)).sum())
    prob_breakdown = {str(k): float(v) for k, v in proba.items()}

    rec_dict = out.get("recommendation") or {}
    gl = body.get("glucose_level") or body.get("Glucose_Level")
    try:
        glf = float(gl) if gl is not None else None
    except (TypeError, ValueError):
        glf = None

    zone = get_glucose_zone(glf) if glf is not None else None
    ketone_high = False
    cds_category = get_glucose_zone_cds(glf, ketone_high=ketone_high)

    tier_to_action = {"Low": "Decrease", "Moderate": "Maintain", "High": "Increase"}
    dosage = SimpleNamespace(
        action=tier_to_action.get(pred, "Maintain"),
        magnitude="Moderate",
        adjustment_score=conf,
        dose_change_units=0,
        summary=rec_dict.get("summary", f"Insulin dose tier: {pred}."),
        detail=" ".join(rec_dict.get("medical", [])[:3]) or "Educational guidance only; not a dosing prescription.",
        context_summary=f"meal_context={body.get('meal_context')}, activity_context={body.get('activity_context')}",
        meal_bolus_units=0.0,
        correction_dose_units=0.0,
    )
    is_high = pred == "High" or (glf is not None and glf > 250) or cds_category == "critical_alert"
    rec_ns = SimpleNamespace(
        is_high_risk=is_high,
        high_risk_reason="Elevated tier or glucose" if is_high else None,
    )

    patient_dict = {
        "glucose_level": glf,
        "glucose_trend": body.get("glucose_trend"),
        "meal_context": body.get("meal_context"),
        "activity_context": body.get("activity_context"),
        "measurement_time": body.get("measurement_time"),
        "time_category": measurement_time_category(body.get("measurement_time")),
    }

    drivers = [
        ExplanationDriver(
            feature="predicted_tier",
            value=conf,
            shap_value=conf,
            clinical_sentence=f"Model tier {pred} (Low / Moderate / High) with P={conf:.0%}.",
        )
    ]
    alt = [
        "If glucose were lower before meals, tier might shift toward Low.",
        "If activity increases consistently, review meal timing with your care team.",
    ]

    return build_response(
        pred,
        conf,
        entropy,
        prob_breakdown,
        patient_dict,
        dosage,
        rec_ns,
        drivers,
        alt,
    )
