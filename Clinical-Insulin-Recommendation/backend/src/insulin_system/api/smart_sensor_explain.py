"""
Smart Sensor SHAP explainability — same ProductionBundle + preprocessor as /predict.

- No legacy InferenceBundle or PatientInput schema.
- SHAP runs on the final scaled feature matrix from ``preprocessor.transform``.
- API returns user-centered ``top_factors`` only (no raw SHAP arrays).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

from .schemas import ExplainResponse, TopFactor

logger = logging.getLogger(__name__)

# Cached explainers keyed by bundle mtime + model name (invalidated when bundle changes)
_explainer_cache: Dict[str, Any] = {}


def _bundle_mtime() -> float:
    from .smart_sensor_engine import smart_sensor_bundle_path

    p = smart_sensor_bundle_path() / "bundle.joblib"
    return float(os.path.getmtime(p)) if p.is_file() else 0.0


def _load_background_matrix() -> Optional[np.ndarray]:
    from .smart_sensor_engine import smart_sensor_bundle_path

    p = smart_sensor_bundle_path() / "shap_background.npy"
    if not p.is_file():
        logger.warning(
            "shap_background.npy missing under model_bundle/; run `python run_pipeline.py` "
            "to generate training SHAP background for /api/explain."
        )
        return None
    return np.load(p)


def _is_tree_model(name: str) -> bool:
    n = name.lower()
    return any(
        x in n
        for x in (
            "random_forest",
            "decision_tree",
            "gradient_boosting",
            "xgboost",
            "lightgbm",
            "lgbm",
            "xgb",
            "extra_trees",
        )
    )


def _human_feature_name(raw: str) -> str:
    """Map encoded / scaled column names to short human labels."""
    f = raw.lower()
    if f in ("hour_sin", "hour_cos"):
        return "Time of day"
    if f.startswith("dow_") or f in ("dow_sin", "dow_cos"):
        return "Day of week"
    if "time_since" in f:
        return "Time since last reading"
    if "meal_context_" in f:
        suf = raw.split("meal_context_", 1)[-1].replace("_", " ").strip().lower()
        meal_map = {
            "after meal": "After meal",
            "before meal": "Before meal",
            "fasting": "Fasting",
        }
        return meal_map.get(suf, suf.title())
    if "activity_context_" in f:
        suf = raw.split("activity_context_", 1)[-1].replace("_", " ").strip().lower()
        act_map = {
            "resting": "Resting activity",
            "active": "Active movement",
            "post exercise": "After exercise",
            "post_exercise": "After exercise",
        }
        return act_map.get(suf, f"Activity ({suf.title()})")
    if "_time_category" in f or f == "_time_category":
        return "Time of day (morning/afternoon/evening/night)"
    if f == "patient_enc":
        return "Patient pattern"
    if "interaction" in f:
        return "Combined health signals"
    mapping = {
        "glucose_level": "Glucose level",
        "glucose_level_poly2": "Glucose pattern (non-linear)",
        "heart_rate": "Heart rate",
        "activity_level": "Wearable activity level",
        "calories_burned": "Calories burned",
        "sleep_duration": "Sleep duration",
        "step_count": "Step count",
        "medication_intake": "Medication use",
        "diet_quality_score": "Diet quality",
        "stress_level": "Stress level",
        "bmi": "BMI",
        "hba1c": "HbA1c",
        "blood_pressure_systolic": "Blood pressure (systolic)",
        "blood_pressure_diastolic": "Blood pressure (diastolic)",
    }
    for k, v in mapping.items():
        if k in f:
            return v
    return raw.replace("_", " ").title()[:56]


def _magnitude_label(abs_val: float, row_max: float) -> str:
    if row_max <= 1e-12:
        return "Small"
    r = abs_val / row_max
    if r >= 0.45:
        return "Strong"
    if r >= 0.18:
        return "Moderate"
    return "Small"


def _user_impact(signed: float, mag: str, predicted_tier: str) -> str:
    """Short, patient-facing impact line (not raw SHAP)."""
    direction = "increase" if signed >= 0 else "decrease"
    tier_hint = f"toward a {predicted_tier} dose tier" if predicted_tier else "for this reading"
    return f"{mag} {direction} in modeled insulin need {tier_hint}"


def _description_for(
    raw_name: str,
    display: str,
    signed: float,
    predicted_tier: str,
) -> str:
    """Plain-language insight; time-aware where relevant."""
    f = raw_name.lower()
    sign_word = "increased" if signed >= 0 else "reduced"
    if "hour" in f or "dow" in f or "time_category" in f:
        return (
            f"{display}: daily and weekly rhythms affect glucose. Here this timing "
            f"{sign_word} the model's attention toward a {predicted_tier} tier. "
            "Evening or post-meal patterns are common—review trends with your care team."
        )
    if "time_since" in f:
        return (
            f"{display}: spacing between readings affects variability; this factor "
            f"{sign_word} the modeled tier. Consistent timing helps interpretation."
        )
    if "meal_context" in f:
        return (
            f"{display}: meal timing affects glucose and insulin needs; this context "
            f"{sign_word} the predicted tier in the model (educational, not a prescription)."
        )
    if "activity_context" in f:
        return (
            f"{display}: activity changes how your body uses insulin; this factor "
            f"{sign_word} the modeled dose tier."
        )
    if "glucose" in f:
        return (
            f"{display}: current glucose strongly influences the tier; this input "
            f"{sign_word} the prediction. This supports discussion with your clinician, not automatic dosing."
        )
    return (
        f"{display}: this signal {sign_word} the model's score toward a {predicted_tier} tier. "
        "Use alongside professional medical advice."
    )


def _entropy(proba: np.ndarray) -> float:
    p = np.clip(np.asarray(proba, dtype=float), 1e-12, 1.0)
    return float(-(p * np.log(p)).sum())


def _shap_row_for_class(shap_out: Any, pred_idx: int, sample_idx: int = 0) -> np.ndarray:
    """
    Normalize SHAP output to shape (n_features,) for the predicted class.

    Handles list (multiclass), 2D, 3D arrays from TreeExplainer / KernelExplainer.
    """
    if isinstance(shap_out, list):
        arr = shap_out[pred_idx]
        a = np.asarray(arr)
        if a.ndim == 2:
            return a[sample_idx].ravel()
        return a.ravel()
    a = np.asarray(shap_out)
    if a.ndim == 3:
        # (samples, features, classes)
        return a[sample_idx, :, pred_idx].ravel()
    if a.ndim == 2:
        return a[sample_idx].ravel()
    return a.ravel()


def _get_or_create_explainer(
    model: Any, model_name: str, background: np.ndarray, *, is_regression: bool = False
) -> Any:
    import shap

    cache_key = f"{_bundle_mtime():.6f}|{model_name}|{background.shape}|r={int(is_regression)}"
    if cache_key in _explainer_cache:
        return _explainer_cache[cache_key]

    bg = np.asarray(background, dtype=np.float64)
    if bg.ndim != 2:
        raise ValueError("Background matrix must be 2D")

    if _is_tree_model(model_name):
        try:
            ex = shap.TreeExplainer(model, bg, feature_perturbation="interventional")
        except Exception as e:
            logger.warning("TreeExplainer interventional failed (%s); using default.", e)
            ex = shap.TreeExplainer(model, bg)
    else:
        bg_sub = bg[: min(80, len(bg))]
        pred_fn = model.predict if is_regression else model.predict_proba
        ex = shap.KernelExplainer(pred_fn, bg_sub)

    _explainer_cache.clear()
    _explainer_cache[cache_key] = ex
    logger.info("SHAP explainer initialized and cached for model=%s", model_name)
    return ex


def _fallback_factors(
    model: Any,
    feature_names: List[str],
    predicted_tier: str,
    pred_class_idx: int,
    top_k: int = 5,
) -> List[TopFactor]:
    """Non-SHAP fallbacks: tree importances or linear coefficients for the predicted class."""
    imp = getattr(model, "feature_importances_", None)
    if imp is not None:
        imp = np.asarray(imp).ravel()
        if len(imp) == len(feature_names):
            order = np.argsort(imp)[::-1][:top_k]
            out: List[TopFactor] = []
            for i in order:
                raw = feature_names[i]
                disp = _human_feature_name(raw)
                mag = _magnitude_label(float(imp[i]), float(imp.max() or 1.0))
                out.append(
                    TopFactor(
                        feature=disp,
                        impact=f"{mag} influence on the model",
                        description=_description_for(raw, disp, 1.0, predicted_tier),
                    )
                )
            return out

    coef = getattr(model, "coef_", None)
    if coef is not None:
        c = np.asarray(coef)
        if c.ndim == 1 and c.shape[0] == len(feature_names):
            w = np.abs(c)
            order = np.argsort(w)[::-1][:top_k]
            out = []
            for j in order:
                raw = feature_names[j]
                disp = _human_feature_name(raw)
                signed = float(c[j])
                mag = _magnitude_label(float(w[j]), float(w.max() or 1.0))
                out.append(
                    TopFactor(
                        feature=disp,
                        impact=_user_impact(signed, mag, predicted_tier),
                        description=_description_for(raw, disp, signed, predicted_tier),
                    )
                )
            return out
        if c.ndim == 2 and c.shape[0] > pred_class_idx and c.shape[1] == len(feature_names):
            w = np.abs(c[pred_class_idx])
            order = np.argsort(w)[::-1][:top_k]
            out = []
            for j in order:
                raw = feature_names[j]
                disp = _human_feature_name(raw)
                signed = float(c[pred_class_idx, j])
                mag = _magnitude_label(float(w[j]), float(w.max() or 1.0))
                out.append(
                    TopFactor(
                        feature=disp,
                        impact=_user_impact(signed, mag, predicted_tier),
                        description=_description_for(raw, disp, signed, predicted_tier),
                    )
                )
            return out

    return []


def run_smart_sensor_explain(body: Dict[str, Any]) -> ExplainResponse:
    """
    Same row construction + ``preprocessor.transform`` as ``/predict``; SHAP on transformed X only.
    """
    import pandas as pd

    from smart_sensor_ml.inference import build_inference_row, validate_inference_payload
    from smart_sensor_ml.persistence import predict_new_data

    validate_inference_payload(body)
    from .smart_sensor_engine import load_smart_sensor_bundle

    bundle = load_smart_sensor_bundle()
    defaults = bundle.metadata.get("numeric_defaults") or {}
    row = build_inference_row(body, defaults)

    df = pd.DataFrame([row])
    X = bundle.preprocessor.transform(df)
    feature_names = list(bundle.preprocessor.selected_features)
    if X.shape[1] != len(feature_names):
        raise RuntimeError("Feature dimension mismatch after transform")

    out = predict_new_data(bundle, row, with_recommendation=False)
    pred_label = str(out["predicted_tier_name"])
    pred_pos = int(out["predicted_tier_index"])
    dose_out = out.get("predicted_insulin_dose")
    proba = out.get("class_probabilities") or {}
    if not proba:
        proba = {pred_label: 1.0}
    confidence = float(proba.get(pred_label, 0.0))
    prob_breakdown = {str(k): float(v) for k, v in proba.items()}
    class_order = list(bundle.class_names)
    uent = _entropy(np.array([proba.get(c, 0.0) for c in class_order]))

    model = bundle.model

    background = _load_background_matrix()
    top_factors: List[TopFactor] = []

    if background is None or len(background) == 0:
        top_factors = _fallback_factors(model, feature_names, pred_label, pred_pos)
        return ExplainResponse(
            predicted_insulin_units=float(dose_out) if dose_out is not None else None,
            predicted_class=pred_label,
            prediction=pred_label,
            confidence=confidence,
            top_factors=top_factors,
            top_drivers=[],
            counterfactuals=[],
            probability_breakdown=prob_breakdown,
            uncertainty_entropy=uent,
        )

    is_reg = bundle.metadata.get("task") == "regression"

    try:
        import shap

        explainer = _get_or_create_explainer(
            model, bundle.model_name, background, is_regression=is_reg
        )
        if _is_tree_model(bundle.model_name):
            shap_out = explainer.shap_values(X)
        else:
            ns = min(100, max(50, 25 * X.shape[1]))
            shap_out = explainer.shap_values(X, nsamples=ns)

        if is_reg:
            arr = np.asarray(shap_out)
            if arr.ndim == 2:
                sv = arr[0].ravel()
            else:
                sv = arr.ravel()
        else:
            sv = _shap_row_for_class(shap_out, pred_pos, sample_idx=0)
        if len(sv) != len(feature_names):
            sv = np.resize(sv, len(feature_names))

        row_max = float(np.max(np.abs(sv))) or 1e-9
        order = np.argsort(np.abs(sv))[::-1][:8]

        for j in order:
            raw = feature_names[j]
            disp = _human_feature_name(raw)
            signed = float(sv[j])
            mag = _magnitude_label(abs(signed), row_max)
            impact = _user_impact(signed, mag, pred_label)
            desc = _description_for(raw, disp, signed, pred_label)
            top_factors.append(TopFactor(feature=disp, impact=impact, description=desc))
    except Exception as e:
        logger.warning("SHAP failed; using coefficient / importance fallback: %s", e)
        top_factors = _fallback_factors(model, feature_names, pred_label, pred_pos)

    return ExplainResponse(
        predicted_insulin_units=float(dose_out) if dose_out is not None else None,
        predicted_class=pred_label,
        prediction=pred_label,
        confidence=confidence,
        top_factors=top_factors[:5],
        top_drivers=[],
        counterfactuals=[],
        probability_breakdown=prob_breakdown,
        uncertainty_entropy=uent,
    )
