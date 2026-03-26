"""
Presentation layer: request validation using domain rules.

Calls the business logic (domain) for validation; builds PatientInput from sanitized body.
Returns structured validation errors for 422 responses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..domain.constants import MIN_NUMERIC_FEATURES_FOR_RELIABLE_PREDICTION
from ..domain.validation import validate_assessment_input
from .schemas import PatientInput

MISSING_NUMERIC_DEFAULT = 0.0
NUMERIC_KEYS = (
    "age", "glucose_level", "physical_activity", "BMI", "HbA1c",
    "weight", "insulin_sensitivity", "sleep_hours", "creatinine",
)
PATIENT_ROW_KEYS = (
    "patient_id", "gender", "family_history", "food_intake", "previous_medications",
    "age", "glucose_level", "physical_activity", "BMI", "HbA1c", "weight",
    "insulin_sensitivity", "sleep_hours", "creatinine",
    "iob", "anticipated_carbs", "glucose_trend", "icr", "isf",
    "ketone_level", "cgm_sensor_error", "typical_daily_insulin",
)


def validate_patient_input(body: Dict[str, Any]) -> Tuple[PatientInput, List[str], List[Dict[str, str]]]:
    """Validate using domain rules and coerce to PatientInput. Returns (patient, warnings, errors)."""
    sanitized, errors = validate_assessment_input(body)
    warnings = _check_numeric_warnings(sanitized, errors)
    row = _build_patient_row(sanitized)
    patient = _to_patient_input(row, errors)
    return patient, warnings, errors


def _check_numeric_warnings(sanitized: Dict[str, Any], errors: List) -> List[str]:
    """Return warnings if few numeric features provided."""
    if errors:
        return []
    provided = sum(1 for k in NUMERIC_KEYS if sanitized.get(k) is not None)
    if provided < MIN_NUMERIC_FEATURES_FOR_RELIABLE_PREDICTION:
        return ["Few numeric features provided; prediction may be less reliable."]
    return []


def _build_patient_row(sanitized: Dict[str, Any]) -> Dict[str, Any]:
    """Build row dict for PatientInput from sanitized body."""
    row = {k: sanitized.get(k) for k in PATIENT_ROW_KEYS}
    if sanitized.get("medication_name") is not None:
        row["medication_name"] = sanitized["medication_name"]
    return row


def _to_patient_input(row: Dict[str, Any], errors: List) -> PatientInput:
    """Coerce row to PatientInput; raise ValueError on failure."""
    try:
        return PatientInput(**row)
    except Exception as e:
        if not errors:
            errors.append({"field": "body", "message": str(e)})
        raise ValueError(f"Invalid patient data: {e}") from e


def patient_input_to_dataframe(patient: PatientInput):
    """Build single-row DataFrame with numeric columns as float."""
    import pandas as pd
    from ..config.schema import DataSchema

    row = patient.to_row_dict()
    schema = DataSchema()
    numeric_cols = list(schema.NUMERIC) + list(getattr(schema, "CONTEXTUAL_IMPUTE", ()))
    for col in numeric_cols:
        row[col] = _coerce_numeric(row.get(col))
    if "glucose_trend" not in row:
        row["glucose_trend"] = "stable"
    return pd.DataFrame([row])


def _coerce_numeric(val: Any) -> float:
    """Coerce value to float; return default for null/invalid."""
    if val is None:
        return MISSING_NUMERIC_DEFAULT
    try:
        return float(val)
    except (TypeError, ValueError):
        return MISSING_NUMERIC_DEFAULT
