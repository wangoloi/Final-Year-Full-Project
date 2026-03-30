"""
API request/response schemas for GlucoSense Clinical Support.

Structured JSON inputs and outputs for prediction, explanation, and recommendation.
Validation rules are enforced in the domain layer; schemas accept validated/sanitized data.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- Request schemas ----------


class PatientInput(BaseModel):
    """
    Single patient record for prediction/explain/recommend.
    Matches training schema. After domain validation, categoricals are strict (Male/Female, etc.).
    """

    patient_id: Optional[str] = Field(None, description="Optional identifier")
    gender: Optional[str] = None
    family_history: Optional[str] = None
    food_intake: Optional[str] = None
    previous_medications: Optional[str] = None
    medication_name: Optional[str] = Field(None, description="Required when previous_medications is Oral")
    age: Optional[float] = None
    glucose_level: Optional[float] = None
    physical_activity: Optional[float] = None
    BMI: Optional[float] = None
    HbA1c: Optional[float] = None
    weight: Optional[float] = None
    insulin_sensitivity: Optional[float] = None
    sleep_hours: Optional[float] = None
    creatinine: Optional[float] = None
    # Type 1 diabetes dosing context (optional; used for insulin stacking check and context summary; also model features)
    iob: Optional[float] = Field(None, description="Insulin on board (mL)")
    anticipated_carbs: Optional[float] = Field(None, description="Anticipated carbohydrates (g)")
    glucose_trend: Optional[str] = Field(None, description="Glucose trend: stable, rising, falling")
    # ICR (1 unit per X g carbs) and ISF (1 unit lowers BG by X mg/dL) for meal/correction dosing
    icr: Optional[float] = Field(None, description="Insulin-to-carb ratio (1 unit per X g carbs)")
    isf: Optional[float] = Field(None, description="Correction factor (1 unit lowers BG by X mg/dL)")
    # CDS Safety Engine inputs
    ketone_level: Optional[str] = Field(None, description="Ketone level: none, trace, small, moderate, large, high")
    cgm_sensor_error: Optional[bool] = Field(None, description="True if CGM reports sensor error; requires finger-stick")
    typical_daily_insulin: Optional[float] = Field(None, description="7-day average total daily insulin (units) for HIGH UNCERTAINTY check")

    @field_validator("age", "glucose_level", "physical_activity", "BMI", "HbA1c", "weight", "insulin_sensitivity", "sleep_hours", "creatinine", "iob", "anticipated_carbs", "icr", "isf", "typical_daily_insulin", mode="before")
    @classmethod
    def coerce_numeric(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def to_row_dict(self) -> Dict[str, Any]:
        """Convert to a single-row dict suitable for DataFrame (schema order)."""
        from ..config.schema import DataSchema
        schema = DataSchema()
        row = {
            schema.PATIENT_ID: self.patient_id or "",
            "gender": self.gender,
            "family_history": self.family_history,
            "food_intake": self.food_intake,
            "previous_medications": self.previous_medications,
            "age": self.age,
            "glucose_level": self.glucose_level,
            "physical_activity": self.physical_activity,
            "BMI": self.BMI,
            "HbA1c": self.HbA1c,
            "weight": self.weight,
            "insulin_sensitivity": self.insulin_sensitivity,
            "sleep_hours": self.sleep_hours,
            "creatinine": self.creatinine,
            "iob": self.iob if self.iob is not None else 0.0,
            "anticipated_carbs": self.anticipated_carbs if self.anticipated_carbs is not None else 0.0,
            "glucose_trend": self.glucose_trend if self.glucose_trend else "stable",
        }
        return row


# ---------- Response schemas (with clinical metadata and disclaimer) ----------

CLINICAL_DISCLAIMER = (
    "This system is a clinical decision support tool, not an autonomous diagnostic system. "
    "All recommendations must be reviewed by a qualified healthcare professional. "
    "Do not use as the sole basis for treatment decisions."
)


class PredictionResponse(BaseModel):
    """Response for POST /predict."""

    predicted_class: str = Field(
        ...,
        description="Insulin dose tier (Low / Moderate / High) derived from regression when applicable",
    )
    predicted_insulin_units: Optional[float] = Field(
        None,
        description="Predicted insulin dose (units) when the Smart Sensor model is regression-based",
    )
    confidence: float = Field(..., ge=0, le=1, description="Probability of predicted class")
    uncertainty_entropy: float = Field(..., ge=0, description="Prediction uncertainty")
    probability_breakdown: Dict[str, float] = Field(..., description="Per-class probabilities")
    feature_names_used: List[str] = Field(default_factory=list, description="Features used by model")
    clinical_disclaimer: str = Field(default=CLINICAL_DISCLAIMER)
    request_id: Optional[str] = None


class ExplanationDriver(BaseModel):
    """Legacy per-feature driver (optional; Smart Sensor uses TopFactor)."""

    feature: str
    value: float
    shap_value: float
    clinical_sentence: Optional[str] = None


class TopFactor(BaseModel):
    """User-centered explanation factor (Smart Sensor /explain)."""

    feature: str = Field(..., description="Human-readable feature label")
    impact: str = Field(..., description="Strength and direction in plain language")
    description: str = Field(..., description="Actionable insight for patients/caregivers")


class ExplainResponse(BaseModel):
    """Response for POST /explain (Smart Sensor pipeline; SHAP on transformed features)."""

    predicted_insulin_units: Optional[float] = Field(
        None,
        description="Predicted insulin dose when regression model is loaded",
    )
    predicted_class: str = Field(..., description="Predicted insulin dose tier (Low / Moderate / High)")
    prediction: str = Field(
        default="",
        description="Same as predicted_class (alias for client compatibility)",
    )
    confidence: float

    @model_validator(mode="after")
    def _sync_prediction_field(self):
        if not (self.prediction or "").strip():
            return self.model_copy(update={"prediction": self.predicted_class})
        return self
    top_factors: List[TopFactor] = Field(
        default_factory=list,
        description="Top contributing factors in plain language (no raw SHAP arrays)",
    )
    top_drivers: List[ExplanationDriver] = Field(
        default_factory=list,
        description="Optional legacy structured drivers; may mirror top_factors",
    )
    counterfactuals: List[Dict[str, Any]] = Field(default_factory=list)
    probability_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-class probabilities (same semantics as /predict)",
    )
    uncertainty_entropy: float = Field(
        default=0.0,
        description="Entropy over class probabilities (higher = less certain)",
    )
    clinical_disclaimer: str = Field(default=CLINICAL_DISCLAIMER)
    request_id: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response for POST /recommend."""

    predicted_class: str
    confidence: float
    uncertainty_entropy: float
    dosage_action: str = Field(..., description="Increase | Decrease | Maintain | None")
    dosage_magnitude: str = Field(..., description="None | Small | Moderate | Large")
    adjustment_score: float = Field(0.0, description="Data-driven adjustment strength (0–1)")
    dose_change_units: int = Field(0, description="Recommended dose change in units (+/-)")
    meal_bolus_units: float = Field(0.0, description="Meal bolus from ICR (carbs/ICR)")
    correction_dose_units: float = Field(0.0, description="Correction dose from ISF")
    recommendation_summary: str
    recommendation_detail: str
    context_summary: str = Field("", description="Why the dose was adjusted (e.g. 'Dose reduced by 20% due to upcoming exercise')")
    # UI Recommendation block (Part 3)
    current_reading_display: str = Field("", description="e.g. '185 mg/dL (High)'")
    trend_display: str = Field("", description="e.g. '↘ Falling Slowly'")
    iob_display: str = Field("", description="e.g. '0.015 mL'")
    system_interpretation: str = Field("", description="What the readings suggest—plain-language explanation for the user")
    recommended_action: str = Field("", description="e.g. 'Inject 2.0 Units (Reduced to account for IOB and Trend)'")
    is_high_risk: bool = Field(..., description="True if flagged for clinician review")
    high_risk_reason: Optional[str] = None
    probability_breakdown: Dict[str, float] = Field(default_factory=dict)
    explanation_drivers: List[ExplanationDriver] = Field(default_factory=list)
    alternative_scenarios: List[str] = Field(default_factory=list)
    clinical_disclaimer: str = Field(default=CLINICAL_DISCLAIMER)
    request_id: Optional[str] = None
    # CDS Safety Engine structured output
    status: str = Field("ok", description="ok | rejected")
    category: str = Field("", description="CDS category: level2_hypoglycemia, level1_hypoglycemia, target_range, hyperglycemia, critical_alert")
    suggested_action: str = Field("", description="CDS-formatted suggested action with Draft Recommendation label")
    rationale: str = Field("", description="Brief clinical rationale (The system suggests...)")
    confidence_level: float = Field(0.0, description="0.0-1.0 confidence score")
    risk_flags: List[str] = Field(default_factory=list, description="e.g. hypoglycemia_alert, high_uncertainty, cgm_error")
    requires_urgent_validation: bool = Field(False, description="True when confidence <0.8")
    contributing_factors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Model features with highest global importance and optional current values",
    )
    uncertainty_factors: List[str] = Field(
        default_factory=list,
        description="Plain-language reasons certainty may be limited (missing data, ambiguous tiers, etc.)",
    )
    clinical_assessment: str = Field(
        "",
        description="Short clinician-style synthesis: context, basis, limitations (decision support only)",
    )


class ModelInfoResponse(BaseModel):
    """Response for GET /model-info."""

    model_name: str
    metric_name: str
    metric_value: float
    feature_names: List[str]
    classes: List[str]
    n_features: int
    clinical_disclaimer: str = Field(default=CLINICAL_DISCLAIMER)


class FeatureImportanceResponse(BaseModel):
    """Response for GET /feature-importance."""

    feature_names: List[str]
    importance: List[float]
    source: str = Field(..., description="e.g. permutation | builtin")
    clinical_disclaimer: str = Field(default=CLINICAL_DISCLAIMER)


# ---------- Validation error (structured 422) ----------


class ValidationErrorItem(BaseModel):
    """Single field error for 422 responses."""

    field: str = Field(..., description="Field name")
    message: str = Field(..., description="Validation message")


class ValidationErrorResponse(BaseModel):
    """Structured validation error response (422)."""

    detail: str = Field(..., description="Summary message")
    errors: List[ValidationErrorItem] = Field(default_factory=list, description="Per-field errors")
