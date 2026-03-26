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
    MEDICATION_NAME_MAX_LENGTH,
    PATIENT_ID_MAX_LENGTH,
    SANITIZE_STRING_MAX_LEN,
    SANITIZE_STRING_SHORT_LEN,
    SANITIZE_STRING_TREND_LEN,
    TYPICAL_DAILY_INSULIN_MAX,
    TYPICAL_DAILY_INSULIN_MIN,
    AGE_MAX,
    AGE_MIN,
    ANTICIPATED_CARBS_MAX_G,
    ANTICIPATED_CARBS_MIN_G,
    BMI_MAX,
    BMI_MIN,
    FOOD_INTAKE_VALUES,
    GLUCOSE_TREND_VALUES,
    GENDER_VALUES,
    GLUCOSE_MAX_MGDL,
    GLUCOSE_MIN_MGDL,
    HBA1C_MAX_PCT,
    HBA1C_MIN_PCT,
    IOB_MAX_ML,
    IOB_MIN_ML,
    PREVIOUS_MEDICATION_VALUES,
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
    "Low": "low", "Medium": "medium", "High": "high",
    "None": "none", "Insulin": "insulin", "Oral": "oral",
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


def validate_food_intake(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """Validate food intake category. Allowed: Low, Medium, High. Normalized to lowercase for encoder."""
    if value is None or value == "":
        return None, None
    s = _sanitize_string(value, SANITIZE_STRING_TREND_LEN)
    if not s:
        return None, None
    if s not in FOOD_INTAKE_VALUES:
        return None, f"Food intake must be one of: {', '.join(FOOD_INTAKE_VALUES)}."
    return _API_TO_TRAINING.get(s, s.lower()), None


def validate_previous_medication(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """Validate previous medication. Allowed: None, Insulin, Oral. Normalized to lowercase for encoder."""
    if value is None or value == "":
        return None, None
    s = _sanitize_string(value, SANITIZE_STRING_SHORT_LEN)
    if not s:
        return None, None
    if s not in PREVIOUS_MEDICATION_VALUES:
        return None, f"Previous medication must be one of: {', '.join(PREVIOUS_MEDICATION_VALUES)}."
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


def validate_medication_name(value: Any, required: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Validate medication name (when Oral is selected). Sanitized, max length."""
    if value is None or value == "":
        if required:
            return None, "Medication name is required when Previous medication is Oral."
        return None, None
    s = _sanitize_string(value, MEDICATION_NAME_MAX_LENGTH)
    if required and not s:
        return None, "Medication name is required when Previous medication is Oral."
    return s if s else None, None


def validate_assessment_input(body: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """
    Apply all domain validation rules to the raw request body.
    Returns (sanitized_body, list of errors).
    Required (core inputs only): age, gender, glucose_level, food_intake, previous_medications;
    medication_name when previous_medications is Oral. All other fields optional (imputed by pipeline).
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

    # Food intake (required)
    food_val, food_err = validate_food_intake(body.get("food_intake"))
    if food_err:
        errors.append({"field": "food_intake", "message": food_err})
    elif not food_val or (isinstance(food_val, str) and not food_val.strip()):
        errors.append({"field": "food_intake", "message": "Food intake is required."})
    out["food_intake"] = food_val

    # Previous medication (required) + medication name when Oral
    prev_val, prev_err = validate_previous_medication(body.get("previous_medications"))
    if prev_err:
        errors.append({"field": "previous_medications", "message": prev_err})
    elif not prev_val or (isinstance(prev_val, str) and not prev_val.strip()):
        errors.append({"field": "previous_medications", "message": "Previous medication is required."})
    out["previous_medications"] = prev_val

    # Glucose level (required; medically valid range)
    gl_val, gl_err = validate_glucose_level(body.get("glucose_level"))
    if gl_err:
        errors.append({"field": "glucose_level", "message": gl_err})
    out["glucose_level"] = gl_val

    medication_required = prev_val == "Oral"
    med_name_val, med_name_err = validate_medication_name(body.get("medication_name"), required=medication_required)
    if med_name_err:
        errors.append({"field": "medication_name", "message": med_name_err})
    if med_name_val is not None:
        out["medication_name"] = med_name_val

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

    # Type 1 dosing context (optional): IOB, anticipated carbs, glucose trend
    iob_val, iob_err = _validate_optional_numeric(
        body.get("iob"), IOB_MIN_ML, IOB_MAX_ML, "Insulin on board (IOB)", "mL"
    )
    if iob_err:
        errors.append({"field": "iob", "message": iob_err})
    out["iob"] = iob_val

    ac_val, ac_err = _validate_optional_numeric(
        body.get("anticipated_carbs"), ANTICIPATED_CARBS_MIN_G, ANTICIPATED_CARBS_MAX_G,
        "Anticipated carbs", "g"
    )
    if ac_err:
        errors.append({"field": "anticipated_carbs", "message": ac_err})
    out["anticipated_carbs"] = ac_val

    gt_val = body.get("glucose_trend")
    if gt_val is not None and gt_val != "":
        s = _sanitize_string(gt_val, SANITIZE_STRING_TREND_LEN).lower()
        if s not in GLUCOSE_TREND_VALUES:
            errors.append({"field": "glucose_trend", "message": f"Glucose trend must be one of: {', '.join(GLUCOSE_TREND_VALUES)}."})
        else:
            out["glucose_trend"] = s
    else:
        out["glucose_trend"] = None

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
    return ["age", "gender", "glucose_level", "food_intake", "previous_medications"]
