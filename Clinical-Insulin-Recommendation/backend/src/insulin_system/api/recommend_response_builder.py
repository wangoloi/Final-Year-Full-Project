"""
Build RecommendationResponse from ML prediction and clinical recommendation.

Separates response assembly from inference logic.
"""
from typing import Any, Dict, List, Optional

import numpy as np

from ..config.schema import get_glucose_zone, get_glucose_zone_cds, _glucose_label_from_zone, _trend_display
from ..domain.constants import (
    CGM_ERROR_CONFIDENCE_CAP,
    FAST_ACTING_CARBS_GRAMS,
    FAST_ACTING_CARBS_LEVEL2_GRAMS,
    HIGH_UNCERTAINTY_CORRECTION_MULTIPLIER,
    KETONE_HIGH_VALUES,
    TYPICAL_CORRECTION_TDD_FRACTION,
)
from ..config.schema import RecommendationConfig
from .schemas import ExplanationDriver, RecommendationResponse


def build_response(
    pred: str,
    confidence: float,
    entropy: float,
    prob_breakdown: Dict[str, float],
    patient_dict: Dict[str, Any],
    dosage: Any,
    rec: Any,
    explanation_drivers: List[ExplanationDriver],
    alt_scenarios: List[str],
) -> RecommendationResponse:
    """Assemble full RecommendationResponse from components."""
    gl = patient_dict.get("glucose_level")
    zone = get_glucose_zone(gl) if gl is not None else None
    ketone_high = _is_ketone_high(patient_dict)
    cds_category = get_glucose_zone_cds(gl, ketone_high=ketone_high)
    hypo_carbs = FAST_ACTING_CARBS_LEVEL2_GRAMS if cds_category == "level2_hypoglycemia" else FAST_ACTING_CARBS_GRAMS

    current_reading_display = _build_current_reading_display(gl, zone)
    trend_display = _trend_display(patient_dict.get("glucose_trend"))
    iob_display = _build_iob_display(patient_dict.get("iob"))
    system_interpretation = _build_system_interpretation(
        zone, patient_dict, dosage, hypo_carbs
    )
    recommended_action = _build_recommended_action(zone, dosage, hypo_carbs)
    risk_flags = _build_risk_flags(patient_dict, cds_category, ketone_high, dosage, rec.is_high_risk)
    cds_confidence = _apply_confidence_caps(confidence, patient_dict.get("cgm_sensor_error"))
    status = "rejected" if cds_category in ("level1_hypoglycemia", "level2_hypoglycemia") else "ok"
    urgent_thresh = getattr(RecommendationConfig(), "cds_urgent_validation_threshold", 0.8)
    requires_urgent_validation = cds_confidence < urgent_thresh
    suggested_action = _build_suggested_action(
        status, patient_dict.get("cgm_sensor_error"), ketone_high, recommended_action, hypo_carbs
    )
    rationale = _build_rationale(system_interpretation, requires_urgent_validation)

    return RecommendationResponse(
        predicted_class=pred,
        confidence=confidence,
        uncertainty_entropy=entropy,
        dosage_action=dosage.action,
        dosage_magnitude=dosage.magnitude,
        adjustment_score=dosage.adjustment_score,
        dose_change_units=dosage.dose_change_units,
        meal_bolus_units=getattr(dosage, "meal_bolus_units", 0.0),
        correction_dose_units=getattr(dosage, "correction_dose_units", 0.0),
        recommendation_summary=dosage.summary,
        recommendation_detail=dosage.detail,
        context_summary=dosage.context_summary,
        current_reading_display=current_reading_display,
        trend_display=trend_display,
        iob_display=iob_display,
        system_interpretation=system_interpretation,
        recommended_action=recommended_action,
        is_high_risk=rec.is_high_risk,
        high_risk_reason=rec.high_risk_reason,
        probability_breakdown=prob_breakdown,
        explanation_drivers=explanation_drivers,
        alternative_scenarios=alt_scenarios,
        status=status,
        category=cds_category,
        suggested_action=suggested_action,
        rationale=rationale,
        confidence_level=cds_confidence,
        risk_flags=risk_flags,
        requires_urgent_validation=requires_urgent_validation,
    )


def _is_ketone_high(patient_dict: Dict[str, Any]) -> bool:
    """Check if ketone level is high."""
    k = patient_dict.get("ketone_level")
    if not k:
        return False
    return str(k).lower() in KETONE_HIGH_VALUES


def _build_current_reading_display(gl: Optional[float], zone: Optional[Dict]) -> str:
    """Build current reading display string."""
    if gl is None:
        return ""
    gl_label = _glucose_label_from_zone(zone)
    if gl_label:
        return f"{gl:.0f} mg/dL ({gl_label})"
    return f"{gl:.0f} mg/dL"


def _build_iob_display(iob_val: Any) -> str:
    """Build IOB display (mL to units: 1 mL = 100 units)."""
    if iob_val is None:
        return "Not provided"
    iob_units = float(iob_val) * 100
    return f"{iob_units:.1f} units"


def _build_system_interpretation(
    zone: Optional[Dict],
    patient_dict: Dict[str, Any],
    dosage: Any,
    hypo_carbs: int,
) -> str:
    """Build plain-language system interpretation."""
    zid = zone.get("id", "") if zone else ""
    iob_val = patient_dict.get("iob")
    dose_units = dosage.dose_change_units
    ctx = (dosage.context_summary or "").lower()

    if zid in ("hypo", "level2_hypo"):
        return f"Your blood sugar is low. Do not take insulin. Treat with {hypo_carbs}g fast-acting carbs first, then recheck in 15 minutes."
    if zid in ("mild_hyper", "moderate_high", "severe_high") and iob_val is not None and float(iob_val) > 0:
        if dose_units <= 0 or "withhold" in ctx or "iob" in ctx:
            return "Your blood sugar is high, but you still have active insulin working. Adding more insulin now could cause a low later."
    if zid == "low_normal":
        return "Your blood sugar is on the lower side. Dose only for the food you eat; reduce the meal dose to avoid going too low."
    if zid == "target":
        return "Your blood sugar is in a good range. Use your usual dose for food; no correction needed."
    if dosage.context_summary:
        return dosage.context_summary
    return dosage.detail or dosage.summary


def _build_recommended_action(zone: Optional[Dict], dosage: Any, hypo_carbs: int) -> str:
    """Build recommended action string."""
    zid = zone.get("id", "") if zone else ""
    dose_units = dosage.dose_change_units
    ctx = dosage.context_summary or ""

    if zid in ("hypo", "level2_hypo"):
        return f"Do not inject. Consume {hypo_carbs}g fast-acting carbs."
    if dose_units > 0:
        reduction = " (Reduced to account for IOB and Trend)" if ("IOB" in ctx or "reduced" in ctx.lower() or "withhold" in ctx.lower()) else ""
        return f"Inject {dose_units:.1f} Units{reduction}."
    if dose_units < 0:
        return f"Reduce dose by {abs(dose_units):.1f} Units."
    if dosage.action and str(dosage.action).lower() in ("maintain", "none"):
        return "Maintain current dose. No change."
    return dosage.summary or "Review recommendation above."


def _build_risk_flags(
    patient_dict: Dict[str, Any],
    cds_category: str,
    ketone_high: bool,
    dosage: Any,
    is_high_risk: bool,
) -> List[str]:
    """Build list of risk flags."""
    flags: List[str] = []
    if patient_dict.get("cgm_sensor_error") is True:
        flags.append("cgm_error")
    if is_high_risk and "high_uncertainty" not in flags:
        flags.append("high_uncertainty")
    if cds_category in ("level1_hypoglycemia", "level2_hypoglycemia"):
        flags.append("hypoglycemia_alert")
    if ketone_high:
        flags.append("high_ketones")
    typical_tdd = patient_dict.get("typical_daily_insulin")
    isf_val = patient_dict.get("isf")
    dose_units = dosage.dose_change_units
    if typical_tdd and isf_val and dose_units > 0:
        try:
            tdd = float(typical_tdd)
            isf = float(isf_val)
            if tdd > 0 and isf > 0:
                typical_correction = tdd * TYPICAL_CORRECTION_TDD_FRACTION
                if dose_units > typical_correction * HIGH_UNCERTAINTY_CORRECTION_MULTIPLIER:
                    flags.append("high_uncertainty")
        except (TypeError, ValueError):
            pass
    return flags


def _apply_confidence_caps(confidence: float, cgm_error: bool) -> float:
    """Apply CGM error confidence cap if applicable."""
    if cgm_error:
        return min(confidence, CGM_ERROR_CONFIDENCE_CAP)
    return confidence


def _build_suggested_action(
    status: str,
    cgm_error: bool,
    ketone_high: bool,
    recommended_action: str,
    hypo_carbs: int = 15,
) -> str:
    """Build CDS suggested action string."""
    if status == "rejected":
        return f"REJECTED: Do not administer insulin. Consume {hypo_carbs}g fast-acting carbs. Manual finger-stick check recommended."
    if cgm_error:
        return "The system suggests withholding insulin until a manual finger-stick confirms glucose. Draft Recommendation."
    if ketone_high:
        return f"The system suggests {recommended_action} Critical Alert: High ketones reported. Verify with finger-stick and ketone check before dosing. Draft Recommendation."
    return f"The system suggests {recommended_action} Draft Recommendation."


def _build_rationale(system_interpretation: str, requires_urgent_validation: bool) -> str:
    """Build rationale string."""
    base = f"The system suggests {system_interpretation}" if system_interpretation else "The system suggests reviewing the recommendation above."
    if requires_urgent_validation:
        base += " Requires Urgent Clinician Validation."
    return base
