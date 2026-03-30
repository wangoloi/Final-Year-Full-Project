"""
Critical alert insertion logic.

Single responsibility: insert alerts for critical glucose conditions.
"""
from typing import Optional

from ...config.schema import get_glucose_zone
from ...domain.constants import (
    FAST_ACTING_CARBS_GRAMS,
    FAST_ACTING_CARBS_LEVEL2_GRAMS,
    GLUCOSE_HYPO_ALERT_MGDL,
    GLUCOSE_LOW_FOR_DOSE_REDUCTION_MGDL,
    GLUCOSE_MODERATE_HIGH_ALERT_MIN_MGDL,
    GLUCOSE_MODERATE_HIGH_MAX_MGDL,
    GLUCOSE_SEVERE_HIGH_ALERT_MIN_MGDL,
)
from ...storage import insert_alert


def check_critical_alerts(
    glucose_level: Optional[float],
    is_high_risk: bool,
    predicted_class: Optional[str],
) -> None:
    """Insert alerts for critical conditions using glucose zone thresholds."""
    if glucose_level is None:
        _check_high_risk_alert(is_high_risk)
        _check_low_glucose_reduce_alert(None, predicted_class)
        return

    gl = float(glucose_level)
    zone = get_glucose_zone(gl)
    if not zone:
        _check_high_risk_alert(is_high_risk)
        _check_low_glucose_reduce_alert(glucose_level, predicted_class)
        return

    zid = zone.get("id", "")
    _insert_glucose_zone_alerts(gl, zid)
    _check_high_risk_alert(is_high_risk)
    _check_low_glucose_reduce_alert(glucose_level, predicted_class)


def _insert_glucose_zone_alerts(gl: float, zid: str) -> None:
    """Insert alerts for hypo, moderate high, severe high zones."""
    if zid == "level2_hypo":
        insert_alert(
            "critical",
            "Hypoglycemia",
            f"Glucose {gl} mg/dL is below {GLUCOSE_HYPO_ALERT_MGDL}. Stop insulin. Consume {FAST_ACTING_CARBS_LEVEL2_GRAMS}g fast-acting carbs.",
        )
        return
    if zid == "hypo":
        insert_alert(
            "critical",
            "Hypoglycemia",
            f"Glucose {gl} mg/dL is below {GLUCOSE_HYPO_ALERT_MGDL}. Stop insulin. Consume {FAST_ACTING_CARBS_GRAMS}g fast-acting carbs.",
        )
        return
    if zid == "moderate_high":
        insert_alert(
            "warning",
            "Moderate hyperglycemia",
            f"Glucose {gl} mg/dL ({GLUCOSE_MODERATE_HIGH_ALERT_MIN_MGDL}–{GLUCOSE_MODERATE_HIGH_MAX_MGDL}). Add correction dose. Check hydration/stress.",
        )
        return
    if zid == "severe_high":
        insert_alert(
            "critical",
            "Severe hyperglycemia",
            f"Glucose {gl} mg/dL above {GLUCOSE_SEVERE_HIGH_ALERT_MIN_MGDL}. Add correction. Check ketones if BG high >2 hours.",
        )


def _check_high_risk_alert(is_high_risk: bool) -> None:
    """Insert alert when recommendation is flagged for review."""
    if not is_high_risk:
        return
    insert_alert(
        "warning",
        "High-risk recommendation",
        "Last recommendation was flagged for clinician review (system less certain than usual).",
    )


def _check_low_glucose_reduce_alert(
    glucose_level: Optional[float],
    predicted_class: Optional[str],
) -> None:
    """Insert alert when system suggests reduce while glucose already low."""
    if not predicted_class or str(predicted_class).lower() != "down":
        return
    if glucose_level is None:
        return
    if float(glucose_level) >= GLUCOSE_LOW_FOR_DOSE_REDUCTION_MGDL:
        return
    insert_alert(
        "warning",
        "Reduce dose with low glucose",
        "System suggests reducing insulin while glucose is already low. Verify before reducing.",
    )
