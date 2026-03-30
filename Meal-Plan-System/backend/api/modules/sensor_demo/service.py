"""Load SmartSensor_DiabetesMonitoring.csv for demo dashboards (in-memory cache)."""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from api.core import config

logger = logging.getLogger(__name__)

# Raw CSV rows after successful read (or [] if file missing / read error).
_raw_rows: list[dict[str, str]] | None = None
_load_error: str | None = None
# True after the first load attempt — avoids caching "empty" before CSV path is valid (order-dependent tests).
_loaded: bool = False


def reset_sensor_demo_cache() -> None:
    """Clear in-memory cache (used by tests; safe to call in dev)."""
    global _raw_rows, _load_error, _loaded
    _raw_rows = None
    _load_error = None
    _loaded = False


def _normalize_row_keys(row: dict[str, str]) -> dict[str, str]:
    """Strip BOM / whitespace from CSV header keys (Windows Excel sometimes adds BOM)."""
    out: dict[str, str] = {}
    for k, v in row.items():
        nk = (k or "").strip().lstrip("\ufeff")
        out[nk] = (v or "").strip()
    return out


def _parse_float(x: str) -> float | None:
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _parse_int(x: str) -> int | None:
    try:
        return int(float(x)) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def load_rows() -> tuple[list[dict[str, Any]], str | None]:
    """Return (normalized rows, error message if file missing)."""
    global _raw_rows, _load_error, _loaded
    if _loaded:
        return _normalize_cached(), _load_error

    _loaded = True
    path = Path(config.SMART_SENSOR_CSV_PATH)
    if not path.is_file():
        _raw_rows = []
        _load_error = f"CSV not found at {path}"
        logger.warning(_load_error)
        return [], _load_error

    raw: list[dict[str, str]] = []
    try:
        with path.open(newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw.append(_normalize_row_keys(row))
    except OSError as e:
        _raw_rows = []
        _load_error = str(e)
        return [], _load_error

    _raw_rows = raw
    _load_error = None
    return _normalize_cached(), None


def _normalize_cached() -> list[dict[str, Any]]:
    assert _loaded
    assert _raw_rows is not None
    out: list[dict[str, Any]] = []
    for r in _raw_rows:
        out.append(
            {
                "patient_id": r.get("Patient_ID", ""),
                "timestamp": r.get("Timestamp", ""),
                "glucose_level": _parse_float(r.get("Glucose_Level", "")),
                "heart_rate": _parse_float(r.get("Heart_Rate", "")),
                "activity_level": _parse_float(r.get("Activity_Level", "")),
                "calories_burned": _parse_float(r.get("Calories_Burned", "")),
                "sleep_duration": _parse_float(r.get("Sleep_Duration", "")),
                "step_count": _parse_int(r.get("Step_Count", "")),
                "insulin_dose": _parse_float(r.get("Insulin_Dose", "")),
                "medication_intake": _parse_int(r.get("Medication_Intake", "")),
                "diet_quality_score": _parse_int(r.get("Diet_Quality_Score", "")),
                "stress_level": _parse_int(r.get("Stress_Level", "")),
                "bmi": _parse_float(r.get("BMI", "")),
                "hba1c": _parse_float(r.get("HbA1c", "")),
                "bp_systolic": _parse_int(r.get("Blood_Pressure_Systolic", "")),
                "bp_diastolic": _parse_int(r.get("Blood_Pressure_Diastolic", "")),
                "predicted_progression": _parse_int(r.get("Predicted_Progression", "")),
            }
        )
    return out


def distinct_patients(limit: int = 100) -> list[str]:
    rows, _ = load_rows()
    seen: list[str] = []
    found = set()
    for r in rows:
        pid = r.get("patient_id") or ""
        if pid and pid not in found:
            found.add(pid)
            seen.append(pid)
            if len(seen) >= limit:
                break
    return sorted(seen)


def series_for_patient(patient_id: str, limit: int = 200) -> list[dict[str, Any]]:
    rows, _ = load_rows()
    pid = (patient_id or "").strip()
    matched = [r for r in rows if (r.get("patient_id") or "") == pid]
    matched.sort(key=lambda x: x.get("timestamp") or "")
    return matched[-limit:]


def summary_for_patient(patient_id: str, last_n: int = 96) -> dict[str, Any]:
    """~24h of 15-min rows when n=96."""
    pts = series_for_patient(patient_id, limit=last_n)
    if not pts:
        return {"patient_id": patient_id, "points": 0, "avg_glucose": None, "latest": None}
    gluc = [p["glucose_level"] for p in pts if p.get("glucose_level") is not None]
    avg = round(sum(gluc) / len(gluc), 1) if gluc else None
    return {
        "patient_id": patient_id,
        "points": len(pts),
        "avg_glucose": avg,
        "latest": pts[-1],
    }


def dataset_meta() -> dict[str, Any]:
    rows, err = load_rows()
    cols = [
        "Patient_ID",
        "Timestamp",
        "Glucose_Level",
        "Heart_Rate",
        "Activity_Level",
        "Calories_Burned",
        "Sleep_Duration",
        "Step_Count",
        "Insulin_Dose",
        "Medication_Intake",
        "Diet_Quality_Score",
        "Stress_Level",
        "BMI",
        "HbA1c",
        "Blood_Pressure_Systolic",
        "Blood_Pressure_Diastolic",
        "Predicted_Progression",
    ]
    return {
        "row_count": len(rows),
        "csv_path": str(Path(config.SMART_SENSOR_CSV_PATH)),
        "columns": cols,
        "load_error": err,
    }
