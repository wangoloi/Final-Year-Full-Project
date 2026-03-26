"""
Domain constants for GlucoSense assessment.

Loads from config/clinical_thresholds.json when available (Uganda Clinical Guideline 2023).
Falls back to hardcoded defaults if config is missing.
"""

from __future__ import annotations


def _load_from_config():
    """Load numeric thresholds from config/clinical_thresholds.json. Returns dict of overrides."""
    try:
        from ..config.clinical_config import get_clinical_thresholds
        cfg = get_clinical_thresholds()
        if not cfg:
            return {}
        g = cfg.get("glucose_mgdl", {})
        return {
            "age_min": cfg.get("age", {}).get("min"),
            "age_max": cfg.get("age", {}).get("max"),
            "glucose_min": cfg.get("glucose_mgdl", {}).get("min"),
            "glucose_max": cfg.get("glucose_mgdl", {}).get("max"),
            "bmi_min": cfg.get("bmi", {}).get("min"),
            "bmi_max": cfg.get("bmi", {}).get("max"),
            "hba1c_min": cfg.get("hba1c_pct", {}).get("min"),
            "hba1c_max": cfg.get("hba1c_pct", {}).get("max"),
            "weight_min": cfg.get("weight_kg", {}).get("min"),
            "weight_max": cfg.get("weight_kg", {}).get("max"),
            "iob_min": cfg.get("iob_ml", {}).get("min"),
            "iob_max": cfg.get("iob_ml", {}).get("max"),
            "carbs_min": cfg.get("anticipated_carbs_g", {}).get("min"),
            "carbs_max": cfg.get("anticipated_carbs_g", {}).get("max"),
            "icr_min": cfg.get("icr", {}).get("min"),
            "icr_max": cfg.get("icr", {}).get("max"),
            "isf_min": cfg.get("isf", {}).get("min"),
            "isf_max": cfg.get("isf", {}).get("max"),
            "tdi_min": cfg.get("typical_daily_insulin", {}).get("min"),
            "tdi_max": cfg.get("typical_daily_insulin", {}).get("max"),
            "glucose_hypo_max": g.get("level1_hypo_max"),
            "glucose_low_normal_min": g.get("low_normal_min"),
            "glucose_low_normal_max": g.get("low_normal_max"),
            "glucose_target_min": g.get("target_min"),
            "glucose_target_max": g.get("target_max"),
            "glucose_mild_hyper_min": g.get("mild_hyper_min"),
            "glucose_mild_hyper_max": g.get("mild_hyper_max"),
            "glucose_moderate_high_min": g.get("moderate_high_min"),
            "glucose_moderate_high_max": g.get("moderate_high_max"),
            "glucose_severe_high_min": g.get("severe_high_min"),
            "glucose_level2_hypo_max": g.get("level2_hypo_max"),
            "glucose_level1_hypo_min": g.get("level1_hypo_min"),
            "glucose_level1_hypo_max": g.get("level1_hypo_max"),
            "glucose_cds_target_min": g.get("cds_target_min"),
            "glucose_cds_target_max": g.get("cds_target_max"),
            "glucose_hypo_alert": g.get("hypo_alert"),
            "glucose_low_for_dose_reduction": g.get("low_for_dose_reduction"),
            "glucose_moderate_high_alert": g.get("moderate_high_min"),
            "glucose_severe_high_alert": g.get("severe_high_min"),
            "fast_acting_carbs": cfg.get("hypoglycemia_treatment", {}).get("fast_acting_carbs_grams"),
            "fast_acting_carbs_level2": cfg.get("hypoglycemia_treatment", {}).get("fast_acting_carbs_level2_grams"),
            "cgm_error_cap": cfg.get("cds_safety", {}).get("cgm_error_confidence_cap"),
            "typical_correction_fraction": cfg.get("cds_safety", {}).get("typical_correction_tdd_fraction"),
            "high_uncertainty_multiplier": cfg.get("cds_safety", {}).get("high_uncertainty_correction_multiplier"),
            "weight_divisor": cfg.get("personalized_max_adjustment", {}).get("weight_divisor"),
            "personalized_floor": cfg.get("personalized_max_adjustment", {}).get("floor"),
        }
    except Exception:
        return {}


_OVERRIDES = _load_from_config()


def _v(key: str, default):
    """Get value from overrides or default."""
    return _OVERRIDES.get(key, default)


# -----------------------------------------------------------------------------
# Age (configurable)
# -----------------------------------------------------------------------------
AGE_MIN = _v("age_min", 0)
AGE_MAX = _v("age_max", 100)

# -----------------------------------------------------------------------------
# Allowed categorical values (strict domain)
# -----------------------------------------------------------------------------
GENDER_VALUES = ("Male", "Female")
FOOD_INTAKE_VALUES = ("Low", "Medium", "High")
PREVIOUS_MEDICATION_VALUES = ("None", "Insulin", "Oral")

# String sanitization / max lengths
MEDICATION_NAME_MAX_LENGTH = 200
PATIENT_ID_MAX_LENGTH = 200
FAMILY_HISTORY_MAX_LENGTH = 200
SANITIZE_STRING_MAX_LEN = 500
SANITIZE_STRING_SHORT_LEN = 50
SANITIZE_STRING_TREND_LEN = 20

# -----------------------------------------------------------------------------
# Medical value ranges (from config/clinical_thresholds.json)
# -----------------------------------------------------------------------------
GLUCOSE_MIN_MGDL = _v("glucose_min", 20)
GLUCOSE_MAX_MGDL = _v("glucose_max", 600)
BMI_MIN = _v("bmi_min", 12)
BMI_MAX = _v("bmi_max", 70)
HBA1C_MIN_PCT = _v("hba1c_min", 4.0)
HBA1C_MAX_PCT = _v("hba1c_max", 20.0)
WEIGHT_MIN_KG = _v("weight_min", 20)
WEIGHT_MAX_KG = _v("weight_max", 300)

# Type 1 diabetes dosing context (optional)
IOB_MIN_ML = _v("iob_min", 0.0)
IOB_MAX_ML = _v("iob_max", 0.5)
ANTICIPATED_CARBS_MIN_G = _v("carbs_min", 0.0)
ANTICIPATED_CARBS_MAX_G = _v("carbs_max", 500.0)
GLUCOSE_TREND_VALUES = ("stable", "rising", "falling")

# -----------------------------------------------------------------------------
# Glucose zone thresholds (mg/dL) - Uganda Clinical Guideline 2023, CDS Safety Engine
# -----------------------------------------------------------------------------
GLUCOSE_HYPO_MAX_MGDL = _v("glucose_hypo_max", 69)
GLUCOSE_LOW_NORMAL_MIN_MGDL = _v("glucose_low_normal_min", 70)
GLUCOSE_LOW_NORMAL_MAX_MGDL = _v("glucose_low_normal_max", 90)
GLUCOSE_TARGET_MIN_MGDL = _v("glucose_target_min", 90)
GLUCOSE_TARGET_MAX_MGDL = _v("glucose_target_max", 130)
GLUCOSE_MILD_HYPER_MIN_MGDL = _v("glucose_mild_hyper_min", 131)
GLUCOSE_MILD_HYPER_MAX_MGDL = _v("glucose_mild_hyper_max", 180)
GLUCOSE_MODERATE_HIGH_MIN_MGDL = _v("glucose_moderate_high_min", 181)
GLUCOSE_MODERATE_HIGH_MAX_MGDL = _v("glucose_moderate_high_max", 250)
GLUCOSE_SEVERE_HIGH_MIN_MGDL = _v("glucose_severe_high_min", 251)
GLUCOSE_LEVEL2_HYPO_MAX_MGDL = _v("glucose_level2_hypo_max", 53)
GLUCOSE_LEVEL1_HYPO_MIN_MGDL = _v("glucose_level1_hypo_min", 54)
GLUCOSE_LEVEL1_HYPO_MAX_MGDL = _v("glucose_level1_hypo_max", 69)
GLUCOSE_CDS_TARGET_MIN_MGDL = _v("glucose_cds_target_min", 70)
GLUCOSE_CDS_TARGET_MAX_MGDL = _v("glucose_cds_target_max", 180)
GLUCOSE_HYPO_ALERT_MGDL = _v("glucose_hypo_alert", 70)
GLUCOSE_LOW_FOR_DOSE_REDUCTION_MGDL = _v("glucose_low_for_dose_reduction", 80)
GLUCOSE_MODERATE_HIGH_ALERT_MIN_MGDL = _v("glucose_moderate_high_alert", 181)
GLUCOSE_SEVERE_HIGH_ALERT_MIN_MGDL = _v("glucose_severe_high_alert", 250)
FAST_ACTING_CARBS_GRAMS = _v("fast_acting_carbs", 15)
FAST_ACTING_CARBS_LEVEL2_GRAMS = _v("fast_acting_carbs_level2", 20)
KETONE_HIGH_VALUES = ("moderate", "large", "high")

# -----------------------------------------------------------------------------
# Validation / recommendation minimums
# -----------------------------------------------------------------------------
MIN_NUMERIC_FEATURES_FOR_RELIABLE_PREDICTION = 3

# -----------------------------------------------------------------------------
# ICR / ISF validation bounds
# -----------------------------------------------------------------------------
ICR_MIN = _v("icr_min", 1.0)
ICR_MAX = _v("icr_max", 50.0)
ISF_MIN = _v("isf_min", 10.0)
ISF_MAX = _v("isf_max", 200.0)
TYPICAL_DAILY_INSULIN_MIN = _v("tdi_min", 0.0)
TYPICAL_DAILY_INSULIN_MAX = _v("tdi_max", 500.0)

# -----------------------------------------------------------------------------
# CDS Safety Engine
# -----------------------------------------------------------------------------
CGM_ERROR_CONFIDENCE_CAP = _v("cgm_error_cap", 0.5)
TYPICAL_CORRECTION_TDD_FRACTION = _v("typical_correction_fraction", 0.1)
HIGH_UNCERTAINTY_CORRECTION_MULTIPLIER = _v("high_uncertainty_multiplier", 2)

# -----------------------------------------------------------------------------
# Personalized max adjustment (weight-based) - Uganda 0.6-1.5 IU/kg/day
# -----------------------------------------------------------------------------
PERSONALIZED_MAX_WEIGHT_DIVISOR = _v("weight_divisor", 25)
PERSONALIZED_MAX_FLOOR = _v("personalized_floor", 2)

# -----------------------------------------------------------------------------
# UI / explanation limits
# -----------------------------------------------------------------------------
EXPLANATION_TOP_K = 5
