"""
Map API PatientInput to clinical_insulin_pipeline rows and dose tiers (regression CDS).
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np

from ..schemas import PatientInput

# Fields that strengthen per-request confidence when present (live patient context).
_LIVE_CONFIDENCE_FIELDS = (
    "age",
    "glucose_level",
    "physical_activity",
    "BMI",
    "HbA1c",
    "weight",
    "insulin_sensitivity",
    "sleep_hours",
    "creatinine",
    "iob",
    "anticipated_carbs",
    "icr",
    "isf",
)
_TIER_CENTERS_IU = np.array([10.0 / 6.0, 5.0, 25.0 / 3.0], dtype=float)
from clinical_insulin_pipeline.schema import InsulinPredictionInput


def patient_to_insulin_row(patient: PatientInput) -> Dict[str, Any]:
    """Build SmartSensor-style row for clinical_insulin_pipeline (defaults fill missing wearables)."""
    gl = float(patient.glucose_level) if patient.glucose_level is not None else 120.0
    act = float(patient.physical_activity) if patient.physical_activity is not None else 50.0
    bmi = float(patient.BMI) if patient.BMI is not None else 25.0
    hba1c = float(patient.HbA1c) if patient.HbA1c is not None else 6.5
    sleep = float(patient.sleep_hours) if patient.sleep_hours is not None else 7.0
    pm = (patient.previous_medications or "").lower()
    med = 1 if "insulin" in pm else 0
    inp = InsulinPredictionInput(
        glucose_level=gl,
        activity_level=act,
        bmi=bmi,
        hba1c=hba1c,
        sleep_duration=sleep,
        medication_intake=med,
        heart_rate=70.0,
        calories_burned=200.0,
        step_count=5000.0,
        diet_quality_score=7.0,
        stress_level=5.0,
        blood_pressure_systolic=130.0,
        blood_pressure_diastolic=80.0,
    )
    return inp.to_feature_row_dict()


def dose_to_display_tier(dose: float) -> str:
    """Human-facing tier on 0–10 IU scale."""
    if dose < 10.0 / 3.0:
        return "Low"
    if dose < 20.0 / 3.0:
        return "Moderate"
    return "High"


def dose_to_rec_class(dose: float) -> str:
    """Maps to RecommendationGenerator keys: down | steady | up."""
    if dose < 10.0 / 3.0:
        return "down"
    if dose < 20.0 / 3.0:
        return "steady"
    return "up"


def _tier_probs_from_dose(dose_iu: float, conf: float) -> Dict[str, float]:
    """Softmax over Low / Moderate / High centers on 0–10 IU; spread tightens when conf is high."""
    d = float(np.clip(dose_iu, 0.0, 10.0))
    temp = float(np.clip(1.75 - 0.85 * conf, 0.35, 1.65))
    logits = -np.abs(_TIER_CENTERS_IU - d) / temp
    p = np.exp(logits - np.max(logits))
    p = p / np.sum(p)
    return {"Low": float(p[0]), "Moderate": float(p[1]), "High": float(p[2])}


def _entropy_from_tier_probs(probs: Dict[str, float]) -> float:
    arr = np.clip(
        np.array([probs["Low"], probs["Moderate"], probs["High"]], dtype=float),
        1e-12,
        1.0,
    )
    arr = arr / np.sum(arr)
    return float(-np.sum(arr * np.log(arr)))


def live_regression_confidence(
    bundle_data: Dict[str, Any],
    patient: PatientInput,
    *,
    predicted_dose_iu: float,
) -> Tuple[float, float, Dict[str, float]]:
    """
    Confidence and tier probabilities using (1) held-out test metrics and (2) live patient context.

    Model quality (RMSE / R²) sets a base; completeness, glucose zone, CGM error, and ketones adjust it.
    """
    tm = bundle_data.get("test_metrics") or {}
    rmse = float(tm.get("rmse", 3.5) or 3.5)
    r2 = float(tm.get("r2", 0.0) or 0.0)
    r2_pos = max(0.0, min(1.0, r2))
    # RMSE on ~0–10 IU scale: lower is better; R² lifts the base when positive.
    q_model = float(np.clip(0.86 - 0.10 * rmse + 0.12 * r2_pos, 0.32, 0.88))

    d = patient.model_dump()
    n_live = sum(1 for k in _LIVE_CONFIDENCE_FIELDS if d.get(k) is not None)
    if n_live <= 3:
        completeness = 0.78
    elif n_live <= 5:
        completeness = 0.9
    else:
        completeness = 1.0

    gl = d.get("glucose_level")
    if gl is None:
        glucose_factor = 0.88
    else:
        try:
            g = float(gl)
            if g < 54 or g > 300:
                glucose_factor = 0.72
            elif g < 70 or g > 250:
                glucose_factor = 0.82
            elif 70 <= g <= 180:
                glucose_factor = 1.0
            else:
                glucose_factor = 0.92
        except (TypeError, ValueError):
            glucose_factor = 0.88

    if d.get("cgm_sensor_error") is True:
        glucose_factor *= 0.85

    kl = (d.get("ketone_level") or "").strip().lower()
    if kl in ("moderate", "large", "high"):
        ketone_factor = 0.8
    elif kl in ("small", "trace"):
        ketone_factor = 0.93
    else:
        ketone_factor = 1.0

    conf = float(np.clip(q_model * completeness * glucose_factor * ketone_factor, 0.22, 0.95))
    probs = _tier_probs_from_dose(predicted_dose_iu, conf)
    entropy = _entropy_from_tier_probs(probs)
    entropy = float(np.clip(entropy, 0.05, 2.0))
    return conf, entropy, probs


def regression_confidence_from_bundle(bundle_data: Dict[str, Any]) -> Tuple[float, float, Dict[str, float]]:
    """
    Bundle-only confidence (no live patient). Prefer :func:`live_regression_confidence` for API paths.
    """
    tm = bundle_data.get("test_metrics") or {}
    r2 = float(tm.get("r2", 0.0) or 0.0)
    conf = float(np.clip(0.55 + 0.4 * max(0.0, min(1.0, r2)), 0.5, 0.95))
    entropy = float(max(0.05, min(2.0, 1.0 - conf)))
    probs = {
        "Low": 0.33,
        "Moderate": 0.34,
        "High": 0.33,
        "down": 0.0,
        "steady": 0.0,
        "up": 0.0,
        "no": 0.0,
    }
    return conf, entropy, probs
