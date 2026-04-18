"""
Recommendation generator: map ML model predictions to clinical recommendations.

Uses RecommendationConfig for all text and thresholds (no hardcoded copy).
Recommendation flow: ML model predict/proba -> this generator -> API response.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..config.schema import RecommendationConfig, get_glucose_zone, get_glucose_zone_cds
from ..config.clinical_config import (
    get_clinical_thresholds,
    get_uganda_daily_dose_range,
    get_uganda_children_under_5,
    get_uganda_basal_bolus_split,
)
from ..domain.constants import (
    FAST_ACTING_CARBS_GRAMS,
    FAST_ACTING_CARBS_LEVEL2_GRAMS,
    GLUCOSE_HYPO_ALERT_MGDL,
    GLUCOSE_MILD_HYPER_MIN_MGDL,
    PERSONALIZED_MAX_WEIGHT_DIVISOR,
    PERSONALIZED_MAX_FLOOR,
)

logger = logging.getLogger(__name__)


def _from_config(section: str, key: str, default):
    """Get value from config/clinical_thresholds.json."""
    cfg = get_clinical_thresholds()
    return (cfg.get(section, {}) or {}).get(key, default)


# Adjustment score (from config/clinical_thresholds.json)
ADJUSTMENT_SCORE_GLUCOSE_DIVISOR = _from_config("adjustment_score", "glucose_divisor", 150.0)
ADJUSTMENT_SCORE_ACTIVITY_DIVISOR = _from_config("adjustment_score", "activity_divisor", 10.0)
ADJUSTMENT_SCORE_HBA1C_DIVISOR = _from_config("adjustment_score", "hba1c_divisor", 10.0)
ADJUSTMENT_SCORE_GLUCOSE_WEIGHT = _from_config("adjustment_score", "glucose_weight", 0.4)
ADJUSTMENT_SCORE_ACTIVITY_WEIGHT = _from_config("adjustment_score", "activity_weight", 0.3)
ADJUSTMENT_SCORE_HBA1C_WEIGHT = _from_config("adjustment_score", "hba1c_weight", 0.3)
ADJUSTMENT_SCORE_DEFAULT_GLUCOSE = _from_config("adjustment_score", "default_glucose", 100.0)
ADJUSTMENT_SCORE_DEFAULT_ACTIVITY = _from_config("adjustment_score", "default_activity", 5.0)
ADJUSTMENT_SCORE_DEFAULT_HBA1C = _from_config("adjustment_score", "default_hba1c", 7.0)
ADJUSTMENT_SCORE_CLIP_MIN = _from_config("adjustment_score", "clip_min", 0.0)
ADJUSTMENT_SCORE_CLIP_MAX = _from_config("adjustment_score", "clip_max", 1.0)

# Confidence -> magnitude mapping (from config)
MAGNITUDE_LARGE_THRESHOLD = _from_config("magnitude_thresholds", "large", 0.8)
MAGNITUDE_MODERATE_THRESHOLD = _from_config("magnitude_thresholds", "moderate", 0.6)
MAGNITUDE_SMALL_THRESHOLD = _from_config("magnitude_thresholds", "small", 0.4)

# Fallback config values when not in RecommendationConfig (from clinical_thresholds.json)
DEFAULT_CONFIDENCE_THRESHOLD = _from_config("recommendation", "confidence_threshold", 0.6)
DEFAULT_UNCERTAINTY_ENTROPY_THRESHOLD = 1.0
DEFAULT_MAX_ADJUSTMENT = _from_config("recommendation", "max_adjustment", 5)
DEFAULT_IOB_SIGNIFICANT_THRESHOLD = _from_config("iob_ml", "significant_threshold", 0.02)
DEFAULT_GLUCOSE_HIGH_FOR_STACKING = _from_config("recommendation", "glucose_high_for_stacking", 180.0)

# Physical activity (from clinical_thresholds.json)
ACTIVITY_HIGH_THRESHOLD = _from_config("activity", "high_threshold", 7)
DOSE_REDUCTION_PCT_FOR_HIGH_ACTIVITY = _from_config("activity", "dose_reduction_pct", 20)
STACKING_RISK_MAX_DECREASE_UNITS = _from_config("stacking_risk", "max_decrease_units", 1)


@dataclass
class DosageSuggestion:
    """Dosage adjustment suggestion with magnitude and confidence."""

    action: str  # Increase | Decrease | Maintain | None
    magnitude: str  # None | Small | Moderate | Large
    confidence: float
    summary: str
    detail: str
    context_summary: str = ""  # Why the dose was adjusted (e.g. "Correction withheld due to high IOB")
    adjustment_score: float = 0.0  # Data-driven adjustment strength (0–1)
    dose_change_units: int = 0  # Recommended dose change in units (+/-)
    meal_bolus_units: float = 0.0  # Meal bolus from ICR (carbs / ICR)
    correction_dose_units: float = 0.0  # Correction from ISF ((glucose - target) / ISF)


@dataclass
class ClinicalRecommendation:
    """Full clinical recommendation for one prediction."""

    predicted_class: str
    confidence: float
    uncertainty_entropy: float
    dosage_suggestion: DosageSuggestion
    is_high_risk: bool
    high_risk_reason: Optional[str] = None
    probability_breakdown: Optional[Dict[str, float]] = None


def compute_adjustment_score(patient_dict: Dict[str, Any], top_driver_names: Optional[List[str]] = None) -> float:
    """Adjustment strength from key features (glucose, activity, metabolic). Returns 0–1."""
    import numpy as np
    g = float(patient_dict.get("glucose_level", ADJUSTMENT_SCORE_DEFAULT_GLUCOSE) or ADJUSTMENT_SCORE_DEFAULT_GLUCOSE) / ADJUSTMENT_SCORE_GLUCOSE_DIVISOR
    a = float(patient_dict.get("physical_activity", ADJUSTMENT_SCORE_DEFAULT_ACTIVITY) or ADJUSTMENT_SCORE_DEFAULT_ACTIVITY) / ADJUSTMENT_SCORE_ACTIVITY_DIVISOR
    h = float(patient_dict.get("HbA1c", ADJUSTMENT_SCORE_DEFAULT_HBA1C) or ADJUSTMENT_SCORE_DEFAULT_HBA1C) / ADJUSTMENT_SCORE_HBA1C_DIVISOR
    score = ADJUSTMENT_SCORE_GLUCOSE_WEIGHT * g + ADJUSTMENT_SCORE_ACTIVITY_WEIGHT * (1.0 - a) + ADJUSTMENT_SCORE_HBA1C_WEIGHT * h
    return float(np.clip(score, ADJUSTMENT_SCORE_CLIP_MIN, ADJUSTMENT_SCORE_CLIP_MAX))


def _uganda_daily_dose_cap_iu(weight_kg: Optional[float], age_years: Optional[float] = None) -> Optional[float]:
    """Uganda Guideline 2023: max daily insulin IU = weight * (0.5 if age<5 else 1.5). Returns None if no weight."""
    if weight_kg is None or weight_kg <= 0:
        return None
    try:
        w = float(weight_kg)
        min_iu, max_iu = get_uganda_daily_dose_range()
        child_iu, child_age = get_uganda_children_under_5()
        if age_years is not None and float(age_years) < child_age:
            return w * child_iu  # Children <5: 0.5 IU/kg, refer to paediatrician
        return w * max_iu  # 1.5 IU/kg/day max
    except (TypeError, ValueError):
        return None


def _uganda_children_refer(age_years: Optional[float]) -> bool:
    """Uganda Guideline: children <5 years should be referred to paediatrician."""
    if age_years is None:
        return False
    try:
        _, child_age = get_uganda_children_under_5()
        return float(age_years) < child_age
    except (TypeError, ValueError):
        return False


def _personalized_max_adjustment(weight_kg: Optional[float], base_max: int = DEFAULT_MAX_ADJUSTMENT) -> int:
    """Personalize max adjustment by weight (Uganda 0.6-1.5 IU/kg/day): lighter patients get lower cap."""
    if weight_kg is None or weight_kg <= 0:
        return base_max
    try:
        w = float(weight_kg)
        # Uganda: cap single adjustment by proportion of daily range; scale 50kg->~3, 70kg->~4, 90kg+->5
        adj = max(PERSONALIZED_MAX_FLOOR, min(base_max, int(PERSONALIZED_MAX_FLOOR + w / PERSONALIZED_MAX_WEIGHT_DIVISOR)))
        return adj
    except (TypeError, ValueError):
        return base_max


def score_to_dose_change(
    score: float,
    pred_class: str,
    max_adjustment: int = DEFAULT_MAX_ADJUSTMENT,
    weight_kg: Optional[float] = None,
) -> int:
    """Map adjustment score + class to dose change (units). Uses personalized max when weight provided."""
    import numpy as np
    max_adj = _personalized_max_adjustment(weight_kg, max_adjustment) if weight_kg else max_adjustment
    base = {"up": 1, "steady": 0, "down": -1, "no": 0}.get(str(pred_class).lower(), 0)
    if base == 0:
        return 0
    delta = int(np.round(score * max_adj))
    delta = np.clip(delta, 1, max_adj) if base > 0 else np.clip(-delta, -max_adj, -1)
    return int(np.clip(delta, -max_adj, max_adj))


def _compute_meal_bolus(anticipated_carbs: float, icr: float) -> float:
    """Meal bolus = carbs / ICR (1 unit per X g carbs)."""
    try:
        if (icr is None or float(icr) <= 0 or
                anticipated_carbs is None or float(anticipated_carbs) <= 0):
            return 0.0
        return max(0.0, float(anticipated_carbs) / float(icr))
    except (TypeError, ValueError):
        return 0.0


def _compute_correction_dose(
    glucose_mgdl: float,
    target_mgdl: float,
    isf: float,
) -> float:
    """Correction dose = (glucose - target) / ISF. Only when glucose > target."""
    try:
        if isf is None or float(isf) <= 0 or glucose_mgdl is None:
            return 0.0
        excess = float(glucose_mgdl) - float(target_mgdl)
        if excess <= 0:
            return 0.0
        return max(0.0, excess / float(isf))
    except (TypeError, ValueError):
        return 0.0


def _check_high_glucose_reduce_without_iob(
    patient_dict: Dict[str, Any],
    dose_change_units: int,
    glucose_hyper_threshold: float = GLUCOSE_MILD_HYPER_MIN_MGDL,
) -> Tuple[int, str]:
    """
    Clinical sanity: when glucose is high (hyperglycemia) and IOB is 0, recommending
    'reduce dose' is counterintuitive—typically you'd add correction. Override to maintain
    and flag for review. The ML model does not use IOB as a feature, so this post-hoc
    check aligns the recommendation with dosing context.
    """
    if dose_change_units >= 0:
        return dose_change_units, ""
    iob = patient_dict.get("iob")
    glucose = patient_dict.get("glucose_level")
    if glucose is None:
        return dose_change_units, ""
    try:
        gl_val = float(glucose)
        iob_val = float(iob) if iob is not None else 0.0
    except (TypeError, ValueError):
        return dose_change_units, ""
    if gl_val < glucose_hyper_threshold or iob_val > 0:
        return dose_change_units, ""
    return 0, (
        "Your blood sugar is high and you have no active insulin. The system suggests keeping your dose as is for now—"
        "please review whether a correction is needed."
    )


def _check_insulin_stacking(
    patient_dict: Dict[str, Any],
    dose_change_units: int,
    iob_threshold: float,
    glucose_high_threshold: float,
) -> Tuple[int, str]:
    """
    Never recommend a dose without checking for insulin stacking.
    If BG is high but trend is downward and IOB is significant, prioritize safety over correction.
    Also: when BG high + IOB significant + trend rising → may be delayed absorption; reduce correction.
    Returns (adjusted_dose_change_units, context_summary).
    """
    iob = patient_dict.get("iob")
    glucose = patient_dict.get("glucose_level")
    trend = patient_dict.get("glucose_trend")
    if iob is None or glucose is None:
        return dose_change_units, ""
    try:
        iob_val = float(iob)
        gl_val = float(glucose)
    except (TypeError, ValueError):
        return dose_change_units, ""
    trend_str = str(trend or "").lower()
    is_downward = trend_str in ("falling", "down")
    is_rising = trend_str in ("rising", "up")
    is_high_bg = gl_val >= glucose_high_threshold
    is_significant_iob = iob_val >= iob_threshold
    iob_display = f"{iob_val:.2f} units"

    # Case 1: BG high, trend down, IOB significant → withhold or reduce correction
    if is_high_bg and is_downward and is_significant_iob:
        if dose_change_units > 0:
            return 0, f"You have {iob_display} of active insulin and your sugar is trending down. Adding more insulin now could cause a low—safety first."
        if dose_change_units < 0:
            reduced = max(dose_change_units, -STACKING_RISK_MAX_DECREASE_UNITS)
            return reduced, f"Dose reduced less aggressively because you have {iob_display} active and sugar is trending down."
        return 0, f"Keep current dose. You have {iob_display} active and sugar is trending down—avoid adding more insulin."

    # Case 2: BG high, IOB significant, trend rising → may be delayed absorption; reduce correction to avoid stacking
    if is_high_bg and is_rising and is_significant_iob and dose_change_units > 0:
        reduced = max(0, dose_change_units - 1)
        if reduced < dose_change_units:
            return reduced, f"You have {iob_display} active insulin and glucose is rising. Correction reduced to avoid stacking—insulin may still be absorbing."
    return dose_change_units, ""


def _magnitude_from_confidence(confidence: float) -> str:
    """Map confidence to suggestion magnitude (for display). Safe for None/NaN."""
    if confidence is None:
        return "None"
    try:
        c = float(confidence)
        if c >= MAGNITUDE_LARGE_THRESHOLD:
            return "Large"
        if c >= MAGNITUDE_MODERATE_THRESHOLD:
            return "Moderate"
        if c >= MAGNITUDE_SMALL_THRESHOLD:
            return "Small"
    except (TypeError, ValueError):
        pass
    return "None"


def _recommendation_config_from_json() -> RecommendationConfig:
    """Build RecommendationConfig from config/clinical_thresholds.json when available."""
    rec = get_clinical_thresholds().get("recommendation", {}) or {}
    return RecommendationConfig(
        default_icr=rec.get("default_icr", 10.0),
        default_isf=rec.get("default_isf", 50.0),
        target_glucose_mgdl=rec.get("target_glucose_mgdl", 100.0),
        confidence_threshold=rec.get("confidence_threshold", 0.75),
        cds_urgent_validation_threshold=rec.get("cds_urgent_validation_threshold", 0.8),
        max_adjustment=int(rec.get("max_adjustment", 5)),
        iob_significant_threshold=rec.get("iob_significant_threshold", 0.02),
        glucose_high_for_stacking=rec.get("glucose_high_for_stacking", 180.0),
    )


class RecommendationGenerator:
    """Maps ML model predictions to clinical recommendations. Uganda T1D Guideline 2023, config/clinical_thresholds.json."""

    def __init__(self, config: Optional[RecommendationConfig] = None):
        self._cfg = config or _recommendation_config_from_json()
        self._rec_map = getattr(self._cfg, "recommendation_content", None) or {}

    def is_high_risk(self, confidence: float, entropy: float) -> Tuple[bool, Optional[str]]:
        """Flag for clinician review: low confidence or high uncertainty (from config thresholds). Safe for None/NaN."""
        reasons = []
        conf = confidence if confidence is not None else 0.0
        ent = entropy if entropy is not None else 0.0
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.0
        try:
            ent = float(ent)
        except (TypeError, ValueError):
            ent = 0.0
        thresh_conf = getattr(self._cfg, "confidence_threshold", None)
        thresh_ent = getattr(self._cfg, "uncertainty_entropy_threshold", None)
        try:
            thresh_conf = float(thresh_conf) if thresh_conf is not None else DEFAULT_CONFIDENCE_THRESHOLD
        except (TypeError, ValueError):
            thresh_conf = DEFAULT_CONFIDENCE_THRESHOLD
        try:
            thresh_ent = float(thresh_ent) if thresh_ent is not None else DEFAULT_UNCERTAINTY_ENTROPY_THRESHOLD
        except (TypeError, ValueError):
            thresh_ent = DEFAULT_UNCERTAINTY_ENTROPY_THRESHOLD
        if conf is None:
            conf = 0.0
        if thresh_conf is None:
            thresh_conf = DEFAULT_CONFIDENCE_THRESHOLD
        if ent is None:
            ent = 0.0
        if thresh_ent is None:
            thresh_ent = DEFAULT_UNCERTAINTY_ENTROPY_THRESHOLD
        if conf < thresh_conf:
            reasons.append(f"System less certain than usual ({conf:.0%} certainty)")
        if ent > thresh_ent:
            reasons.append("Several treatment options could fit; please review the full picture")
        if reasons:
            return True, "; ".join(reasons)
        return False, None

    def generate(
        self,
        predicted_class: str,
        confidence: float,
        uncertainty_entropy: float,
        probability_breakdown: Optional[Dict[str, float]] = None,
        patient_dict: Optional[Dict[str, Any]] = None,
        top_driver_names: Optional[List[str]] = None,
    ) -> ClinicalRecommendation:
        """
        Build clinical recommendation from ML prediction and confidence/uncertainty.
        predicted_class comes from the model; text from config.
        If patient_dict and top_driver_names provided, computes adjustment_score and dose_change_units.
        """
        key = str(predicted_class).lower()
        rec = self._rec_map.get(key) or self._rec_map.get("steady") or {}
        if not rec:
            rec = {"summary": "Review the suggestion.", "action": "Maintain", "magnitude": "None", "detail": "Manual review recommended."}

        magnitude = rec.get("magnitude", "Moderate")
        if magnitude == "Moderate":
            magnitude = _magnitude_from_confidence(confidence if confidence is not None else 0.0)

        conf_val = confidence if confidence is not None else 0.0
        try:
            conf_val = float(conf_val)
        except (TypeError, ValueError):
            conf_val = 0.0
        ent_val = uncertainty_entropy if uncertainty_entropy is not None else 0.0
        try:
            ent_val = float(ent_val)
        except (TypeError, ValueError):
            ent_val = 0.0

        max_adj = getattr(self._cfg, "max_adjustment", DEFAULT_MAX_ADJUSTMENT) or DEFAULT_MAX_ADJUSTMENT
        thresh = getattr(self._cfg, "confidence_threshold", 0.75) or 0.75

        # Always compute adjustment score and dose change so the clinician has full context
        adj_score = 0.0
        dose_change_units = 0
        meal_bolus_units = 0.0
        correction_dose_units = 0.0
        context_parts: List[str] = []
        if patient_dict:
            gl = patient_dict.get("glucose_level")
            zone = get_glucose_zone(gl) if gl is not None else None

            # Glucose zone override: suspend insulin logic for hypo; apply zone-specific rules
            if zone:
                zid = zone.get("id", "")
                if zid in ("hypo", "level2_hypo"):
                    cds_category = get_glucose_zone_cds(gl)
                    carbs_grams = FAST_ACTING_CARBS_LEVEL2_GRAMS if cds_category == "level2_hypoglycemia" else FAST_ACTING_CARBS_GRAMS
                    return ClinicalRecommendation(
                        predicted_class=predicted_class,
                        confidence=conf_val,
                        uncertainty_entropy=ent_val,
                        dosage_suggestion=DosageSuggestion(
                            action="None",
                            magnitude="None",
                            confidence=conf_val,
                            summary=f"STOP: Hypoglycemia. Suspend all insulin. Consume {carbs_grams}g fast-acting carbs.",
                            detail=zone.get("action", ""),
                            context_summary=f"Glucose below {GLUCOSE_HYPO_ALERT_MGDL} mg/dL—insulin logic suspended; treat low first.",
                            adjustment_score=ADJUSTMENT_SCORE_CLIP_MIN,
                            dose_change_units=0,
                        ),
                        is_high_risk=True,
                        high_risk_reason=f"Hypoglycemia: glucose below {GLUCOSE_HYPO_ALERT_MGDL} mg/dL. Treat with {carbs_grams}g fast-acting carbs before any insulin.",
                        probability_breakdown=probability_breakdown,
                    )
                if zid == "low_normal":
                    context_parts.append("Blood sugar 70–90: dose only for food; reduce meal dose to avoid going too low.")
                elif zid == "mild_hyper":
                    context_parts.append("Blood sugar slightly high: a small correction may help, but only if you have little active insulin on board.")
                elif zid == "moderate_high":
                    context_parts.append("Blood sugar elevated: consider a correction dose and check hydration or stress.")
                elif zid == "severe_high":
                    context_parts.append("Blood sugar very high: add a correction dose. Check for ketones if it stays high for more than 2 hours.")

            adj_score = compute_adjustment_score(patient_dict, top_driver_names or [])
            weight_kg = patient_dict.get("weight")
            dose_change_units = score_to_dose_change(adj_score, predicted_class, max_adj, weight_kg=weight_kg)

            # ICR/ISF-based meal bolus and correction (when provided)
            icr = patient_dict.get("icr") or getattr(self._cfg, "default_icr", 10.0)
            isf = patient_dict.get("isf") or getattr(self._cfg, "default_isf", 50.0)
            target_gl = getattr(self._cfg, "target_glucose_mgdl", 100.0)
            ac = patient_dict.get("anticipated_carbs")
            gl = patient_dict.get("glucose_level")
            if ac is not None and ac > 0 and icr:
                meal_bolus_units = _compute_meal_bolus(float(ac), float(icr))
            if gl is not None and isf and float(gl) > target_gl:
                correction_dose_units = _compute_correction_dose(float(gl), target_gl, float(isf))
            if zone and zone.get("id") == "low_normal":
                dose_change_units = min(0, dose_change_units)  # No increase in low-normal

            # Insulin stacking check: never recommend without checking; prioritize safety
            iob_thresh = getattr(self._cfg, "iob_significant_threshold", DEFAULT_IOB_SIGNIFICANT_THRESHOLD) or DEFAULT_IOB_SIGNIFICANT_THRESHOLD
            gl_thresh = getattr(self._cfg, "glucose_high_for_stacking", DEFAULT_GLUCOSE_HIGH_FOR_STACKING) or DEFAULT_GLUCOSE_HIGH_FOR_STACKING
            # First: sanity check—high glucose + IOB=0 + reduce → override (model doesn't use IOB)
            dose_change_units, high_gl_no_iob_ctx = _check_high_glucose_reduce_without_iob(
                patient_dict, dose_change_units, glucose_hyper_threshold=GLUCOSE_MILD_HYPER_MIN_MGDL
            )
            if high_gl_no_iob_ctx:
                context_parts.append(high_gl_no_iob_ctx)
            # Then: insulin stacking check (high IOB + high BG + trend down → withhold/reduce correction)
            dose_change_units, stacking_ctx = _check_insulin_stacking(
                patient_dict, dose_change_units, float(iob_thresh), float(gl_thresh)
            )
            if stacking_ctx:
                context_parts.append(stacking_ctx)

            # Uganda Guideline 2023: cap dose so total daily does not exceed 1.5 IU/kg (0.5 if age<5)
            age_val = patient_dict.get("age")
            typical_tdd = patient_dict.get("typical_daily_insulin")
            uganda_cap = _uganda_daily_dose_cap_iu(weight_kg, float(age_val) if age_val is not None else None)
            if uganda_cap is not None and typical_tdd is not None and dose_change_units > 0:
                try:
                    tdd = float(typical_tdd)
                    headroom = max(0, uganda_cap - tdd)
                    if dose_change_units > headroom:
                        dose_change_units = int(headroom)
                        context_parts.append(f"Per Uganda guidelines, total daily dose capped at {uganda_cap:.0f} IU (weight-based).")
                except (TypeError, ValueError):
                    pass

            # Uganda Guideline: children <5 refer to paediatrician
            if _uganda_children_refer(age_val):
                context_parts.append("Uganda Guideline: Children under 5 years—start 0.5 IU/kg/day and refer to paediatrician.")

            # Uganda regimen context (basal-bolus 40-50% evening, premixed 2/3 morning 1/3 evening)
            try:
                bb_min, bb_max = get_uganda_basal_bolus_split()
                context_parts.append(f"Uganda T1D: Basal-bolus (evening 40-50%) or premixed 2/3 morning, 1/3 evening.")
            except Exception:
                pass

            # Build context from other factors when no stacking override
            if not stacking_ctx:
                activity = patient_dict.get("physical_activity")
                if activity is not None:
                    try:
                        act_val = float(activity)
                        if act_val >= ACTIVITY_HIGH_THRESHOLD and dose_change_units > 0:
                            pct = DOSE_REDUCTION_PCT_FOR_HIGH_ACTIVITY
                            context_parts.append(f"Dose reduced by {pct}% because you have high physical activity planned.")
                            dose_change_units = max(0, int(dose_change_units * (1 - pct / 100)))
                        elif act_val >= ACTIVITY_HIGH_THRESHOLD and dose_change_units == 0:
                            context_parts.append("Dose kept the same; activity may lower your blood sugar.")
                    except (TypeError, ValueError):
                        pass
                ac = patient_dict.get("anticipated_carbs")
                if ac is not None and ac > 0 and dose_change_units <= 0 and str(predicted_class).lower() == "up":
                    context_parts.append(f"You have {ac:.0f}g carbs planned; dose for the meal separately.")
                if not context_parts:
                    context_parts.append("Dose based on your current blood sugar, active insulin, and planned carbs.")

        # Assist the clinician: always provide the suggestion; flag for review when certainty is low
        summary = rec.get("summary", "")
        detail = rec.get("detail", "")
        if conf_val < thresh:
            summary = f"{summary} Consider with caution: the system is less certain than usual ({conf_val:.0%} certainty)."
            detail = f"{detail} Use your clinical judgment: the system is less sure about this suggestion. Review the patient's full picture before deciding."
            if not context_parts:
                context_parts.append("The system is less certain than usual; please review the full picture.")

        context_summary = " ".join(context_parts).strip() if context_parts else "Recommendation based on your blood sugar, active insulin, and planned carbs."

        # When any check overrides dose to 0, align action with safety
        final_action = rec.get("action", "Maintain")
        if dose_change_units == 0:
            if str(final_action).lower() in ("increase", "decrease"):
                final_action = "Maintain"
                magnitude = "None"

        if meal_bolus_units > 0 or correction_dose_units > 0:
            parts = []
            if meal_bolus_units > 0:
                parts.append(f"Meal bolus: {meal_bolus_units:.1f} units")
            if correction_dose_units > 0:
                parts.append(f"Correction: {correction_dose_units:.1f} units")
            if parts and context_summary:
                context_summary = "; ".join(parts) + ". " + context_summary
            elif parts:
                context_summary = "; ".join(parts)

        dosage = DosageSuggestion(
            action=final_action,
            magnitude=magnitude,
            confidence=conf_val,
            summary=summary,
            detail=detail,
            context_summary=context_summary,
            adjustment_score=adj_score,
            dose_change_units=dose_change_units,
            meal_bolus_units=meal_bolus_units,
            correction_dose_units=correction_dose_units,
        )
        is_risk, reason = self.is_high_risk(confidence, uncertainty_entropy)
        if patient_dict and patient_dict.get("cgm_sensor_error") is True:
            is_risk = True
            reason = (reason or "") + " CGM sensor error reported. Manual finger-stick check required."
        if patient_dict and patient_dict.get("ketone_level"):
            kt = str(patient_dict.get("ketone_level", "")).lower()
            if kt in ("moderate", "large", "high"):
                is_risk = True
                reason = (reason or "") + " High ketone levels reported. Verify before dosing."
        if patient_dict and _uganda_children_refer(patient_dict.get("age")):
            is_risk = True
            reason = (reason or "") + " Uganda Guideline: Children under 5 years—refer to paediatrician."
        return ClinicalRecommendation(
            predicted_class=predicted_class,
            confidence=conf_val,
            uncertainty_entropy=ent_val,
            dosage_suggestion=dosage,
            is_high_risk=is_risk,
            high_risk_reason=reason,
            probability_breakdown=probability_breakdown,
        )


