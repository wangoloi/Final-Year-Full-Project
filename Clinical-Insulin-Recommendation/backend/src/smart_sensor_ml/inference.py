"""§12 Inference helpers — validate inputs and build SmartSensor-shaped rows."""
from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

import pandas as pd

from smart_sensor_ml import config

logger = logging.getLogger(__name__)

# Accept API-style snake_case or CSV column names
_ALIASES: Dict[str, str] = {
    "glucose_level": "Glucose_Level",
    "heart_rate": "Heart_Rate",
    "activity_level": "Activity_Level",
    "calories_burned": "Calories_Burned",
    "sleep_duration": "Sleep_Duration",
    "step_count": "Step_Count",
    "medication_intake": "Medication_Intake",
    "diet_quality_score": "Diet_Quality_Score",
    "stress_level": "Stress_Level",
    "blood_pressure_systolic": "Blood_Pressure_Systolic",
    "blood_pressure_diastolic": "Blood_Pressure_Diastolic",
}


def validate_inference_payload(body: Mapping[str, Any]) -> None:
    """§2, §16 — reject incomplete requests (especially missing time context)."""
    for k in (config.COL_MEASUREMENT_TIME, config.COL_MEAL_CONTEXT, config.COL_ACTIVITY_CONTEXT):
        v = body.get(k)
        if v is None or (isinstance(v, str) and not str(v).strip()):
            raise ValueError(f"Missing required field: {k}")
    ts = body.get(config.COL_MEASUREMENT_TIME)
    try:
        pd.to_datetime(ts, errors="raise")
    except Exception as e:
        raise ValueError(f"Invalid measurement_time timestamp: {e}") from e
    meal = str(body.get(config.COL_MEAL_CONTEXT, "")).strip().lower()
    act = str(body.get(config.COL_ACTIVITY_CONTEXT, "")).strip().lower()
    if meal not in config.MEAL_CONTEXT_VALUES:
        raise ValueError(f"meal_context must be one of {config.MEAL_CONTEXT_VALUES}")
    if act not in config.ACTIVITY_CONTEXT_VALUES:
        raise ValueError(f"activity_context must be one of {config.ACTIVITY_CONTEXT_VALUES}")
    gl = body.get("Glucose_Level") or body.get("glucose_level")
    if gl is None:
        raise ValueError("Missing required field: glucose_level (or Glucose_Level)")
    try:
        g = float(gl)
    except (TypeError, ValueError):
        raise ValueError("glucose_level must be numeric") from None
    if not (40.0 <= g <= 500.0):
        raise ValueError("glucose_level outside realistic range [40, 500] mg/dL")


def _get_numeric(body: Mapping[str, Any], col: str, defaults: Mapping[str, float]) -> float:
    if col in body and body[col] is not None:
        try:
            return float(body[col])
        except (TypeError, ValueError):
            pass
    for alias, csv_name in _ALIASES.items():
        if csv_name == col and alias in body and body[alias] is not None:
            try:
                return float(body[alias])
            except (TypeError, ValueError):
                pass
    return float(defaults.get(col, 0.0))


def build_inference_row(
    body: Mapping[str, Any],
    numeric_defaults: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """
    Build one SmartSensor-shaped dict for preprocessor.transform (single-row DataFrame).

    `numeric_defaults` should be training medians from ProductionBundle.metadata.
    """
    defaults = dict(numeric_defaults or {})
    validate_inference_payload(body)

    pid = body.get(config.COL_PATIENT) or body.get("patient_id") or "UNKNOWN"
    mt = body.get(config.COL_MEASUREMENT_TIME)
    ts_str = mt if isinstance(mt, str) else pd.Timestamp(mt).isoformat()

    row: Dict[str, Any] = {
        config.COL_PATIENT: str(pid),
        config.COL_TIME: ts_str,
        config.COL_MEASUREMENT_TIME: ts_str,
        config.COL_MEAL_CONTEXT: str(body[config.COL_MEAL_CONTEXT]).strip().lower(),
        config.COL_ACTIVITY_CONTEXT: str(body[config.COL_ACTIVITY_CONTEXT]).strip().lower(),
        config.COL_TARGET: 0.0,
    }
    for col in config.NUMERIC_FEATURES:
        row[col] = _get_numeric(body, col, defaults)

    return row


def measurement_time_category(ts: Any) -> str:
    """Derive morning/afternoon/evening/night label for recommendations."""
    t = pd.to_datetime(ts, errors="coerce")
    if pd.isna(t):
        return "unknown"
    h = int(t.hour) % 24
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 22:
        return "evening"
    return "night"
