"""
GlucoSense inference: clinical insulin dose regression bundle (clinical_insulin_pipeline).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from clinical_insulin_pipeline.inference import predict_insulin_dose
from clinical_insulin_pipeline.models import get_feature_importance_vector

from ..persistence import InferenceBundle
from ..recommendation.recommendation_generator import RecommendationGenerator
from .helpers.clinical_bridge import (
    dose_to_display_tier,
    dose_to_rec_class,
    live_regression_confidence,
    patient_to_insulin_row,
)
from .helpers.clinical_narrative import (
    build_contributing_factors,
    collect_uncertainty_factors,
    top_feature_drivers,
)
from .recommend_response_builder import build_response
from .schemas import (
    FeatureImportanceResponse,
    ModelInfoResponse,
    PatientInput,
    PredictionResponse,
    RecommendationResponse,
)

logger = logging.getLogger(__name__)


def get_bundle(model_dir: Optional[Path] = None) -> InferenceBundle:
    from ..persistence import load_best_model

    return load_best_model(model_dir)


def _predict_dose_iu(bundle: InferenceBundle, patient: PatientInput) -> float:
    row = patient_to_insulin_row(patient)
    return predict_insulin_dose(bundle.data, row)


def run_predict(patient: PatientInput, df: pd.DataFrame, bundle: InferenceBundle) -> PredictionResponse:
    dose = _predict_dose_iu(bundle, patient)
    tier = dose_to_display_tier(dose)
    conf, entropy, probs = live_regression_confidence(
        bundle.data, patient, predicted_dose_iu=dose
    )
    return PredictionResponse(
        predicted_class=tier,
        predicted_insulin_units=dose,
        confidence=conf,
        uncertainty_entropy=entropy,
        probability_breakdown={k: float(v) for k, v in probs.items() if k in ("Low", "Moderate", "High")},
        feature_names_used=bundle.feature_names,
    )


def run_recommend(
    patient: PatientInput,
    df: pd.DataFrame,
    bundle: InferenceBundle,
    X_background: Optional[np.ndarray] = None,
) -> RecommendationResponse:
    dose = _predict_dose_iu(bundle, patient)
    tier = dose_to_display_tier(dose)
    rec_key = dose_to_rec_class(dose)
    conf, entropy, tier_probs = live_regression_confidence(
        bundle.data, patient, predicted_dose_iu=dose
    )

    patient_dict: Dict[str, Any] = patient.model_dump()
    drivers = top_feature_drivers(bundle.data, bundle.feature_names, k=3)
    top_driver_names = [d["feature"] for d in drivers]
    contributing_factors = build_contributing_factors(drivers, patient_dict)
    uncertainty_factors = collect_uncertainty_factors(
        conf, entropy, patient_dict, tier_probs
    )

    gen = RecommendationGenerator()
    clin = gen.generate(
        rec_key,
        conf,
        entropy,
        probability_breakdown=tier_probs,
        patient_dict=patient_dict,
        top_driver_names=top_driver_names or None,
    )
    prob_out = clin.probability_breakdown if clin.probability_breakdown else tier_probs
    return build_response(
        tier,
        conf,
        entropy,
        prob_out,
        patient_dict,
        clin.dosage_suggestion,
        clin,
        [],
        [],
        contributing_factors=contributing_factors,
        uncertainty_factors=uncertainty_factors,
    )


def get_model_info(bundle: InferenceBundle) -> ModelInfoResponse:
    tm = bundle.data.get("test_metrics") or {}
    rmse = float(tm.get("rmse", 0.0) or 0.0)
    name = bundle.data.get("best_model_name") or bundle.model_name
    return ModelInfoResponse(
        model_name=str(name),
        metric_name="rmse",
        metric_value=rmse,
        feature_names=bundle.feature_names,
        classes=["Low", "Moderate", "High"],
        n_features=len(bundle.feature_names),
    )


def get_feature_importance(bundle: InferenceBundle, evaluation_dir: Path) -> Optional[FeatureImportanceResponse]:
    model = bundle.data.get("model")
    names = bundle.feature_names
    if model is None or not names:
        return None
    imp = get_feature_importance_vector(model, len(names))
    if imp is None or len(imp) != len(names):
        return None
    return FeatureImportanceResponse(
        feature_names=names,
        importance=[float(x) for x in imp],
        source="builtin",
    )
