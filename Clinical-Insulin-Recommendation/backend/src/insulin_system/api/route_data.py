"""
Route data structures and constants.

Separates data definitions from business logic.
"""
from typing import Any, Dict, Tuple

# Person-centric fields to store in records for Reports
INPUT_SUMMARY_KEYS = (
    "glucose_level", "iob", "anticipated_carbs", "glucose_trend",
    "age", "food_intake", "physical_activity", "weight", "BMI", "HbA1c",
    "icr", "isf",
    "ketone_level", "cgm_sensor_error", "typical_daily_insulin",
    "measurement_time", "meal_context", "activity_context",
)

# API defaults
DEFAULT_RECORDS_LIMIT = 100
CHART_MISSING_GLUCOSE_DEFAULT = 0.0
DEFAULT_NOTIFICATIONS_LIMIT = 20
DEFAULT_ALERTS_LIMIT = 50
DEFAULT_GLUCOSE_TRENDS_HOURS = 72
SHAP_BACKGROUND_SAMPLE_SIZE = 100
RANDOM_SEED = 42
REPORTS_DOWNLOAD_NOTIFICATION_TYPE = "reports_download"


def build_input_summary(body: Dict[str, Any]) -> Dict[str, Any]:
    """Build person-centric input summary for Reports."""
    out: Dict[str, Any] = {}
    for k in INPUT_SUMMARY_KEYS:
        v = body.get(k)
        if v is not None and (not isinstance(v, str) or str(v).strip() != ""):
            out[k] = v
    return out if out else {"n_fields": len(body)}
