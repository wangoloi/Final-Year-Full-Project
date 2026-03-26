"""
GlucoSense inference engine: prediction and recommendation (legacy InferenceBundle).

POST /explain uses Smart Sensor SHAP only (see smart_sensor_explain). This module
still provides run_predict and run_recommend for the legacy bundle path.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..config.schema import DashboardConfig
from ..persistence import load_best_model, InferenceBundle
from .schemas import (
    ExplanationDriver,
    PatientInput,
    PredictionResponse,
    RecommendationResponse,
    ModelInfoResponse,
    FeatureImportanceResponse,
)
from .recommend_response_builder import build_response

logger = logging.getLogger(__name__)

# Module-level bundle (lazy load)
_bundle: Optional[InferenceBundle] = None
_config: Optional[DashboardConfig] = None
_shap_explainer: Optional[Any] = None
_background_X: Optional[np.ndarray] = None


def get_bundle(model_dir: Optional[Path] = None) -> InferenceBundle:
    """Load and cache the inference bundle."""
    global _bundle, _config
    if _bundle is None:
        cfg = DashboardConfig()
        if model_dir:
            cfg = DashboardConfig(best_model_dir=model_dir)
        _config = cfg
        _bundle = load_best_model(cfg.best_model_dir)
        
        # If the loaded bundle is a Python dict (from old dump), wrap it.
        if isinstance(_bundle, dict):
            # Create an InferenceBundle class from persistence manually since legacy saving bypassed
            from ..persistence.bundle import InferenceBundle
            new_bundle = InferenceBundle.__new__(InferenceBundle)
            new_bundle.__dict__.update(_bundle)
            _bundle = new_bundle
            
        logger.info("Loaded inference bundle: %s", getattr(_bundle, "model_name", "Unknown"))
    return _bundle


def _get_shap_explainer(bundle: InferenceBundle, X_background: np.ndarray) -> Optional[Any]:
    """Lazy-fit SHAP explainer on a background sample (e.g. from reference data)."""
    global _shap_explainer, _background_X
    if _shap_explainer is not None and _background_X is not None and X_background.shape[1] == _background_X.shape[1]:
        return _shap_explainer
    try:
        from ..explainability import SHAPExplainer
        explainer = SHAPExplainer()
        explainer.fit(bundle._model, X_background, bundle.feature_names)
        _shap_explainer = explainer
        _background_X = X_background
        return _shap_explainer
    except Exception as e:
        logger.warning("SHAP explainer not available: %s", e)
        return None


def run_predict(patient: PatientInput, df: pd.DataFrame, bundle: InferenceBundle) -> PredictionResponse:
    """Run prediction only. Returns structured response with confidence and probabilities."""
    X = bundle.transform(df)
    pred = bundle.predict(X)[0]
    proba = bundle.predict_proba(X)[0]
    classes = list(bundle.classes_)
    idx = list(classes).index(pred)
    confidence = float(proba[idx])
    entropy = float(-(proba * np.log(proba + 1e-10)).sum())
    prob_breakdown = {str(c): float(proba[i]) for i, c in enumerate(classes)}
    return PredictionResponse(
        predicted_class=str(pred),
        confidence=confidence,
        uncertainty_entropy=entropy,
        probability_breakdown=prob_breakdown,
        feature_names_used=bundle.feature_names,
    )


def _safe_confidence(proba: np.ndarray, idx: int) -> float:
    """Extract confidence from proba at idx; clamp to [0,1]."""
    try:
        c = float(proba[idx]) if proba[idx] is not None else 0.0
    except (TypeError, ValueError):
        c = 0.0
    if np.isnan(c) or c < 0 or c > 1:
        return 0.0
    return c


def _safe_entropy(proba: np.ndarray) -> float:
    """Compute entropy from proba; return 0 if invalid."""
    try:
        e = float(-(proba * np.log(proba + 1e-10)).sum())
    except (TypeError, ValueError):
        return 0.0
    if np.isnan(e) or e < 0:
        return 0.0
    return e


def _prob_breakdown_from_proba(proba: np.ndarray, classes: List) -> Dict[str, float]:
    """Build probability breakdown dict from proba array."""
    out = {}
    for i, c in enumerate(classes):
        try:
            p = proba[i]
            out[str(c)] = float(p) if p is not None else 0.0
        except (TypeError, ValueError):
            out[str(c)] = 0.0
    return out


def _patient_to_dict(patient: PatientInput) -> Dict[str, Any]:
    """Build patient dict from PatientInput for recommendation."""
    d = dict(patient.to_row_dict()) if patient else {}
    if not patient:
        return d
    for key in ("iob", "anticipated_carbs", "glucose_trend", "icr", "isf", "ketone_level", "cgm_sensor_error", "typical_daily_insulin"):
        val = getattr(patient, key, None)
        if val is not None:
            d[key] = val
    return d


def _get_recommend_explanation_drivers(
    bundle: InferenceBundle,
    X: np.ndarray,
    X_background: Optional[np.ndarray],
    pred: str,
    classes: List,
    prob_breakdown: Dict[str, float],
) -> Tuple[List[ExplanationDriver], List[str]]:
    """Get SHAP-based explanation drivers and alternative scenarios."""
    explainer = _get_shap_explainer(bundle, X_background) if X_background is not None and len(X_background) > 0 else None
    drivers: List[ExplanationDriver] = []
    cf: List[Dict[str, Any]] = []
    if explainer is not None:
        try:
            from ..explainability.clinical_report import CLINICAL_FEATURE_NAMES
            sv = explainer._explainer.shap_values(X)
            sv_one = sv[0] if isinstance(sv, list) else sv[0]
            x_row = X[0]
            order = np.argsort(np.abs(sv_one))[::-1][:10]
            for i in order:
                fname = bundle.feature_names[i] if i < len(bundle.feature_names) else f"feature_{i}"
                clinical_name = CLINICAL_FEATURE_NAMES.get(fname, fname)
                drivers.append(ExplanationDriver(
                    feature=fname,
                    value=float(x_row[i]),
                    shap_value=float(sv_one[i]),
                    clinical_sentence=f"{clinical_name} (value={x_row[i]:.2f}).",
                ))
            cf = explainer.counterfactual(x_row, sv_one, str(pred), np.array(classes), bundle.feature_names)
        except Exception:
            pass
    alt_scenarios = [c.get("suggestion", str(c)) for c in cf[:5]] if cf else [
        "If glucose or HbA1c were lower, the system might suggest maintaining or reducing dosage.",
        "If glucose or HbA1c were higher, the system might suggest increasing dosage.",
    ]
    if not drivers:
        for c, p in list(prob_breakdown.items())[:5]:
            drivers.append(ExplanationDriver(feature=c, value=p, shap_value=p, clinical_sentence=f"P({c}) = {p:.0%}."))
    return drivers, alt_scenarios


def run_recommend(
    patient: PatientInput,
    df: pd.DataFrame,
    bundle: InferenceBundle,
    X_background: Optional[np.ndarray] = None,
) -> RecommendationResponse:
    """Run full recommendation: ML prediction + clinical recommendation + explanation."""
    from ..recommendation import RecommendationGenerator

    X = bundle.transform(df)
    pred = bundle.predict(X)[0]
    proba = bundle.predict_proba(X)[0]
    _log_mlflow_if_active(pred, proba, bundle)
    classes = list(bundle.classes_)
    idx = list(classes).index(pred)
    confidence = _safe_confidence(proba, idx)
    entropy = _safe_entropy(proba)
    prob_breakdown = _prob_breakdown_from_proba(proba, classes)
    patient_dict = _patient_to_dict(patient)

    rec_gen = RecommendationGenerator()
    rec = rec_gen.generate(str(pred), confidence, entropy, prob_breakdown, patient_dict=patient_dict, top_driver_names=None)
    dosage = rec.dosage_suggestion

    explanation_drivers, alt_scenarios = _get_recommend_explanation_drivers(
        bundle, X, X_background, str(pred), classes, prob_breakdown
    )

    return build_response(
        str(pred),
        confidence,
        entropy,
        prob_breakdown,
        patient_dict,
        dosage,
        rec,
        explanation_drivers,
        alt_scenarios,
    )


def _log_mlflow_if_active(pred: Any, proba: np.ndarray, bundle: InferenceBundle) -> None:
    """Log to MLflow if active run exists."""
    try:
        import mlflow
        if mlflow.active_run() or mlflow.get_tracking_uri():
            mlflow.log_metric("recommend_predicted_class_hash", hash(str(pred)) % 1000)
            mlflow.log_metric("recommend_confidence", float(proba[list(bundle.classes_).index(pred)]))
    except Exception:
        pass


def get_model_info(bundle: InferenceBundle) -> ModelInfoResponse:
    """Model metadata and performance metrics for GET /model-info."""
    meta = getattr(bundle, "to_metadata", lambda: {})()
    if not meta:
        meta = {
            "model_name": bundle.model_name,
            "metric_name": getattr(bundle, "metric_name", "f1_weighted"),
            "metric_value": getattr(bundle, "metric_value", 0.0),
            "feature_names": bundle.feature_names,
            "classes": list(bundle.classes_),
        }
    return ModelInfoResponse(
        model_name=meta.get("model_name", bundle.model_name),
        metric_name=meta.get("metric_name", "f1_weighted"),
        metric_value=float(meta.get("metric_value", 0)),
        feature_names=meta.get("feature_names", bundle.feature_names),
        classes=meta.get("classes", list(bundle.classes_)),
        n_features=len(meta.get("feature_names", bundle.feature_names)),
    )


def get_feature_importance(bundle: InferenceBundle, evaluation_dir: Path) -> Optional[FeatureImportanceResponse]:
    """Load feature importance from model (built-in) or evaluation artifacts."""
    est = bundle._model
    if hasattr(est, "named_steps") and "clf" in getattr(est, "named_steps", {}):
        est = est.named_steps["clf"]
    importance = None
    if hasattr(est, "feature_importances_"):
        importance = est.feature_importances_.tolist()
    elif hasattr(est, "coef_"):
        coef = np.asarray(est.coef_)
        importance = np.mean(np.abs(coef), axis=0).tolist()
    if importance is not None and len(importance) == len(bundle.feature_names):
        return FeatureImportanceResponse(
            feature_names=bundle.feature_names,
            importance=importance,
            source="builtin",
        )
    return None
