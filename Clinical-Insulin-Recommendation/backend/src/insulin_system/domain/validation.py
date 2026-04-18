"""
Business logic: domain validation rules for assessment inputs.

No database or framework code. Pure, testable validation.
Used by the API layer to enforce strict domain constraints before calling the engine.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    FAMILY_HISTORY_MAX_LENGTH,
    ICR_MAX,
    ICR_MIN,
    ISF_MAX,
    ISF_MIN,
    PATIENT_ID_MAX_LENGTH,
    SANITIZE_STRING_MAX_LEN,
    SANITIZE_STRING_SHORT_LEN,
    SANITIZE_STRING_TREND_LEN,
    TYPICAL_DAILY_INSULIN_MAX,
    TYPICAL_DAILY_INSULIN_MIN,
    AGE_MAX,
    AGE_MIN,
    BMI_MAX,
    BMI_MIN,
    GLUCOSE_TREND_VALUES,
    GENDER_VALUES,
    GLUCOSE_MAX_MGDL,
    GLUCOSE_MIN_MGDL,
    HBA1C_MAX_PCT,
    HBA1C_MIN_PCT,
    WEIGHT_MAX_KG,
    WEIGHT_MIN_KG,
)


class ValidationError(Exception):
    """Structured validation error with field and message."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def _sanitize_string(value: Any, max_len: int = SANITIZE_STRING_MAX_LEN) -> str:
    """Strip and truncate; remove control characters to prevent injection."""
    if value is None:
        return ""
    s = str(value).strip()
    s = re.sub(r"[\x00-\x1f\x7f]", "", s)
    return s[:max_len] if len(s) > max_len else s


def validate_age(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Validate age. Returns (coerced_value, error_message).
    Accepts only realistic human ages in [AGE_MIN, AGE_MAX].
    """
    if value is None or value == "":
        return None, None  # Optional field
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None, "Age must be a number."
    if n != int(n) or n < 0:
        return None, "Age must be a non-negative whole number."
    n = int(n)
    if n < AGE_MIN or n > AGE_MAX:
        return None, f"Age must be between {AGE_MIN} and {AGE_MAX}."
    return float(n), None


# Map API values (capitalized) to training-data format (lowercase) for encoder compatibility
_API_TO_TRAINING = {
    "Male": "male", "Female": "female",
    "Yes": "yes", "No": "no",
}


def validate_gender(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """Validate gender. Allowed: Male, Female. Returns (value, error_message). Normalized to lowercase for encoder."""
    if value is None or value == "":
        return None, None
    s = _sanitize_string(value, SANITIZE_STRING_SHORT_LEN)
    if not s:
        return None, None
    if s not in GENDER_VALUES:
        return None, f"Gender must be one of: {', '.join(GENDER_VALUES)}."
    return _API_TO_TRAINING.get(s, s.lower()), None


def validate_glucose_level(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Validate blood glucose (mg/dL). Required; must be in medically plausible range.
    Returns (coerced_value, error_message).
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, "Glucose level is required for recommendation."
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None, "Glucose must be a number."
    if n < GLUCOSE_MIN_MGDL or n > GLUCOSE_MAX_MGDL:
        return None, f"Glucose must be between {GLUCOSE_MIN_MGDL} and {GLUCOSE_MAX_MGDL} mg/dL."
    return n, None


def _validate_optional_numeric(
    value: Any,
    min_val: float,
    max_val: float,
    field_name: str,
    unit: str = "",
) -> Tuple[Optional[float], Optional[str]]:
    """Validate optional numeric field; if provided must be in [min_val, max_val]. Returns (value, error)."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be a number."
    if n < min_val or n > max_val:
        u = f" {unit}" if unit else ""
        return None, f"{field_name} must be between {min_val} and {max_val}{u}."
    return n, None


def validate_bmi(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """Optional BMI (kg/m²). If provided, must be in [BMI_MIN, BMI_MAX]."""
    return _validate_optional_numeric(value, BMI_MIN, BMI_MAX, "BMI", "kg/m²")


def validate_hba1c(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """Optional HbA1c (%). If provided, must be in [HBA1C_MIN_PCT, HBA1C_MAX_PCT]."""
    return _validate_optional_numeric(value, HBA1C_MIN_PCT, HBA1C_MAX_PCT, "HbA1c", "%")


def validate_weight(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """Optional weight (kg). If provided, must be in [WEIGHT_MIN_KG, WEIGHT_MAX_KG]."""
    return _validate_optional_numeric(value, WEIGHT_MIN_KG, WEIGHT_MAX_KG, "Weight", "kg")


def validate_assessment_input(body: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """
    Apply all domain validation rules to the raw request body.
    Returns (sanitized_body, list of errors).
    Required (core inputs only): age, gender, glucose_level.
    All other fields optional (imputed by pipeline).
    """
    errors: List[Dict[str, str]] = []
    out: Dict[str, Any] = {}

    # Age (required)
    age_val, age_err = validate_age(body.get("age"))
    if age_err:
        errors.append({"field": "age", "message": age_err})
    elif age_val is None and not (body.get("age") is not None and str(body.get("age")).strip()):
        errors.append({"field": "age", "message": "Age is required."})
    out["age"] = age_val

    # Gender (required)
    gender_val, gender_err = validate_gender(body.get("gender"))
    if gender_err:
        errors.append({"field": "gender", "message": gender_err})
    elif not gender_val or (isinstance(gender_val, str) and not gender_val.strip()):
        errors.append({"field": "gender", "message": "Gender is required."})
    out["gender"] = gender_val

    # Glucose level (required; medically valid range)
    gl_val, gl_err = validate_glucose_level(body.get("glucose_level"))
    if gl_err:
        errors.append({"field": "glucose_level", "message": gl_err})
    out["glucose_level"] = gl_val

    # Optional numeric with medical range validation (BMI, HbA1c, weight)
    bmi_val, bmi_err = validate_bmi(body.get("BMI"))
    if bmi_err:
        errors.append({"field": "BMI", "message": bmi_err})
    out["BMI"] = bmi_val

    hba1c_val, hba1c_err = validate_hba1c(body.get("HbA1c"))
    if hba1c_err:
        errors.append({"field": "HbA1c", "message": hba1c_err})
    out["HbA1c"] = hba1c_val

    weight_val, weight_err = validate_weight(body.get("weight"))
    if weight_err:
        errors.append({"field": "weight", "message": weight_err})
    out["weight"] = weight_val

    # Dosing-context inputs removed from API/UI; model uses safe defaults internally.

    # Ketone level (optional; high = critical alert)
    kt = body.get("ketone_level")
    if kt is not None and str(kt).strip():
        s = _sanitize_string(kt, SANITIZE_STRING_SHORT_LEN).lower()
        out["ketone_level"] = s
    else:
        out["ketone_level"] = None

    # CGM sensor error (optional; triggers LOW confidence + finger-stick)
    cgm_err = body.get("cgm_sensor_error")
    if cgm_err is not None:
        try:
            out["cgm_sensor_error"] = bool(cgm_err)
        except (TypeError, ValueError):
            out["cgm_sensor_error"] = None
    else:
        out["cgm_sensor_error"] = None

    # Typical daily insulin / 7-day average (optional; for HIGH UNCERTAINTY check)
    tdi_val, tdi_err = _validate_optional_numeric(body.get("typical_daily_insulin"), TYPICAL_DAILY_INSULIN_MIN, TYPICAL_DAILY_INSULIN_MAX, "Typical daily insulin", "units")
    if tdi_err:
        errors.append({"field": "typical_daily_insulin", "message": tdi_err})
    out["typical_daily_insulin"] = tdi_val

    # ICR and ISF (optional; for meal/correction dosing)
    icr_val, icr_err = _validate_optional_numeric(body.get("icr"), ICR_MIN, ICR_MAX, "ICR (insulin-to-carb ratio)", "")
    if icr_err:
        errors.append({"field": "icr", "message": icr_err})
    out["icr"] = icr_val

    isf_val, isf_err = _validate_optional_numeric(body.get("isf"), ISF_MIN, ISF_MAX, "ISF (correction factor)", "mg/dL")
    if isf_err:
        errors.append({"field": "isf", "message": isf_err})
    out["isf"] = isf_val

    # Other optional fields (coerce only; pipeline will impute if missing)
    for key in (
        "patient_id",
        "family_history",
        "physical_activity",
        "insulin_sensitivity",
        "sleep_hours",
        "creatinine",
    ):
        if key not in body:
            continue
        v = body[key]
        if v is None or v == "":
            out[key] = None
            continue
        if key == "patient_id":
            out[key] = _sanitize_string(v, PATIENT_ID_MAX_LENGTH) if v else None
        elif key == "family_history":
            s = _sanitize_string(v, FAMILY_HISTORY_MAX_LENGTH) if v else None
            out[key] = _API_TO_TRAINING.get(s, s.lower() if s else None) if s else None
        else:
            try:
                out[key] = float(v)
            except (TypeError, ValueError):
                out[key] = None

    return out, errors


def get_required_fields_for_recommendation() -> List[str]:
    """Fields that must be non-empty for a valid recommendation request (core inputs only)."""
    return ["age", "gender", "glucose_level"]
