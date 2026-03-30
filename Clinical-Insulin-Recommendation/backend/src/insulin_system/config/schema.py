"""
Data and pipeline schema definitions.

Centralizes column names, clinical bounds, and pipeline settings
to support testability and single source of truth (SLID).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _default_smart_sensor_bundle_dir() -> Path:
    """Override with env SMART_SENSOR_BUNDLE_DIR (absolute or relative to cwd)."""
    p = os.environ.get("SMART_SENSOR_BUNDLE_DIR", "").strip()
    if p:
        return Path(p)
    return Path("outputs/clinical_insulin_pipeline/latest")

from ..domain.constants import (
    FAST_ACTING_CARBS_GRAMS,
    FAST_ACTING_CARBS_LEVEL2_GRAMS,
    GLUCOSE_CDS_TARGET_MAX_MGDL,
    GLUCOSE_CDS_TARGET_MIN_MGDL,
    GLUCOSE_HYPO_MAX_MGDL,
    GLUCOSE_LEVEL1_HYPO_MAX_MGDL,
    GLUCOSE_LEVEL1_HYPO_MIN_MGDL,
    GLUCOSE_LEVEL2_HYPO_MAX_MGDL,
    GLUCOSE_LOW_NORMAL_MIN_MGDL,
    GLUCOSE_LOW_NORMAL_MAX_MGDL,
    GLUCOSE_MODERATE_HIGH_MAX_MGDL,
    GLUCOSE_MODERATE_HIGH_MIN_MGDL,
    GLUCOSE_SEVERE_HIGH_MIN_MGDL,
    GLUCOSE_TARGET_MIN_MGDL,
    GLUCOSE_TARGET_MAX_MGDL,
    GLUCOSE_MILD_HYPER_MIN_MGDL,
    GLUCOSE_MILD_HYPER_MAX_MGDL,
)


@dataclass(frozen=True)
class DataSchema:
    """Column names and types for the insulin dosage dataset."""

    # Identifiers
    PATIENT_ID: str = "patient_id"

    # Target (classification: Insulin; regression: Insulin_Dose)
    TARGET: str = "Insulin"
    TARGET_REGRESSION: str = "Insulin_Dose"

    # Categorical features (nominal/ordinal as per domain)
    CATEGORICAL: Tuple[str, ...] = (
        "gender",
        "family_history",
        "food_intake",
        "previous_medications",
    )

    # Continuous/numeric features
    NUMERIC: Tuple[str, ...] = (
        "age",
        "glucose_level",
        "physical_activity",
        "BMI",
        "HbA1c",
        "weight",
        "insulin_sensitivity",
        "sleep_hours",
        "creatinine",
    )

    # Contextual features (optional at load; added with defaults for training, real values at inference)
    CONTEXTUAL_NUMERIC: Tuple[str, ...] = ("iob", "anticipated_carbs", "glucose_trend_encoded")
    # Contextual columns present at imputation time (glucose_trend_encoded is created in feature engineering)
    CONTEXTUAL_IMPUTE: Tuple[str, ...] = ("iob", "anticipated_carbs")

    # Columns to exclude from modeling (e.g. IDs)
    EXCLUDE_FROM_FEATURES: Tuple[str, ...] = (PATIENT_ID,)

    @property
    def feature_columns(self) -> Tuple[str, ...]:
        """All columns used as model features (categorical + numeric + contextual, excluding ID)."""
        return self.CATEGORICAL + self.NUMERIC + self.CONTEXTUAL_NUMERIC

    @property
    def all_columns(self) -> Tuple[str, ...]:
        """All dataset columns in canonical order."""
        return (self.PATIENT_ID,) + self.CATEGORICAL + self.NUMERIC + (self.TARGET,)


@dataclass(frozen=True)
class ClinicalBounds:
    """
    Clinically plausible bounds for numeric features.

    Used for outlier detection and validation. Values outside these ranges
    may be capped or flagged. Bounds are (min, max) inclusive where applicable.
    """

    # Age in years (pediatric to very elderly)
    AGE: Tuple[float, float] = (18.0, 120.0)
    # Blood glucose mg/dL (fasting and post-prandial range)
    GLUCOSE_LEVEL: Tuple[float, float] = (20.0, 600.0)
    # Activity score (dataset-specific scale)
    PHYSICAL_ACTIVITY: Tuple[float, float] = (0.0, 15.0)
    # BMI kg/m²
    BMI: Tuple[float, float] = (10.0, 70.0)
    # HbA1c %
    HBA1C: Tuple[float, float] = (3.5, 20.0)
    # Weight kg
    WEIGHT: Tuple[float, float] = (25.0, 250.0)
    # Insulin sensitivity (dataset-specific)
    INSULIN_SENSITIVITY: Tuple[float, float] = (0.1, 3.0)
    # Sleep hours per day
    SLEEP_HOURS: Tuple[float, float] = (0.0, 24.0)
    # Serum creatinine mg/dL
    CREATININE: Tuple[float, float] = (0.2, 15.0)
    # IOB (insulin on board) mL; U-100: 1 mL = 100 units
    IOB: Tuple[float, float] = (0.0, 5.0)
    # Anticipated carbohydrates (g)
    ANTICIPATED_CARBS: Tuple[float, float] = (0.0, 300.0)
    # glucose_trend_encoded: stable=0, rising=1, falling=-1
    GLUCOSE_TREND_ENCODED: Tuple[float, float] = (-1.0, 1.0)

    def get_bounds_for_column(self, column: str) -> Tuple[float, float]:
        """Return (min, max) for a numeric column. Raises KeyError if unknown."""
        mapping = {
            "age": self.AGE,
            "glucose_level": self.GLUCOSE_LEVEL,
            "physical_activity": self.PHYSICAL_ACTIVITY,
            "BMI": self.BMI,
            "HbA1c": self.HBA1C,
            "weight": self.WEIGHT,
            "insulin_sensitivity": self.INSULIN_SENSITIVITY,
            "sleep_hours": self.SLEEP_HOURS,
            "creatinine": self.CREATININE,
            "iob": self.IOB,
            "anticipated_carbs": self.ANTICIPATED_CARBS,
            "glucose_trend_encoded": self.GLUCOSE_TREND_ENCODED,
        }
        if column not in mapping:
            raise KeyError(f"No clinical bounds defined for column: {column}")
        return mapping[column]


@dataclass
class EDAPathConfig:
    """Paths for EDA output artifacts."""

    output_dir: Path = field(default_factory=lambda: Path("outputs/eda"))
    missing_plot: str = "missing_values.png"
    distributions_plot: str = "distributions.png"
    correlation_plot: str = "correlation_matrix.png"
    target_plot: str = "target_distribution.png"
    outliers_plot: str = "outliers_boxplot.png"
    summary_file: str = "eda_summary.txt"

    def ensure_output_dir(self) -> Path:
        """Create output directory if it does not exist. Returns the path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    """
    Configuration for the Feature Engineering module.
    Domain-driven interaction pairs, polynomial variables, and aggregates.
    """

    # Interaction pairs: (col_a, col_b) -> feature name will be f"{a}_{b}_interaction"
    INTERACTION_PAIRS: Tuple[Tuple[str, str], ...] = (
        ("glucose_level", "insulin_sensitivity"),
        ("BMI", "physical_activity"),
        ("HbA1c", "glucose_level"),
        ("weight", "insulin_sensitivity"),
        ("age", "BMI"),
        ("iob", "anticipated_carbs"),  # Contextual: IOB x carbs for meal dosing
    )
    # Numeric columns to use for polynomial features (degree 2)
    POLYNOMIAL_COLUMNS: Tuple[str, ...] = (
        "glucose_level",
        "HbA1c",
        "BMI",
        "insulin_sensitivity",
    )
    POLYNOMIAL_DEGREE: int = 2
    # Aggregate definitions: name -> list of (column, weight) for weighted sum (normalized)
    # We'll implement metabolic_risk, glycemic_burden as weighted combos
    AGGREGATE_WEIGHTS: Tuple[Tuple[str, Tuple[Tuple[str, float], ...]], ...] = (
        (
            "metabolic_risk_score",
            (("glucose_level", 0.4), ("HbA1c", 0.35), ("BMI", 0.25)),
        ),
        (
            "glycemic_burden",
            (("glucose_level", 0.5), ("HbA1c", 0.5)),
        ),
    )
    # Temporal: column to use as order (e.g. patient_id); None to skip temporal features
    TEMPORAL_ORDER_COLUMN: Optional[str] = "patient_id"
    # Feature selection: method = "mutual_info" | "f_classif" | "variance" | "domain_only" | "none"
    SELECTION_METHOD: str = "mutual_info"
    SELECTION_K: Optional[int] = 35  # Keep top K features; None = no limit for statistical selection
    VARIANCE_THRESHOLD: float = 1e-5  # For variance-based pre-filter
    # Domain: always keep these (by base name or pattern)
    DOMAIN_KEEP: Tuple[str, ...] = (
        "glucose_level",
        "HbA1c",
        "BMI",
        "insulin_sensitivity",
        "age",
        "physical_activity",
        "iob",
        "anticipated_carbs",
        "glucose_trend_encoded",
        "glucose_zone_numeric",
    )
    DOMAIN_DROP: Tuple[str, ...] = ()  # Explicit drops if any


@dataclass
class PipelineConfig:
    """Pipeline-level configuration."""

    # Regression mode: predict continuous Insulin_Dose (True) vs categorical Insulin (False)
    regression_mode: bool = False
    # Split type: "temporal" (by patient_id) or "random" (stratified for classification only)
    split_type: str = "temporal"
    # 80% train, 10% validation, 10% test
    train_ratio: float = 0.8
    # Validation fraction of the remainder (10% of total)
    val_ratio: float = 0.5
    # Test is the rest
    # test_ratio = 1 - train_ratio - val_ratio
    random_state: int = 42
    # Outlier handling: "clip" to bounds, "remove", or "flag"
    outlier_strategy: str = "clip"
    # Missing value strategy: "median" for numeric, "mode" for categorical
    missing_numeric_strategy: str = "median"
    missing_categorical_strategy: str = "mode"
    # Scaling method for continuous features
    scaler_type: str = "standard"  # standard | minmax | robust


@dataclass
class ModelConfig:
    """Configuration for model development: tuning, CV, and class imbalance."""

    # Cross-validation
    cv_folds: int = 5
    stratify_cv: bool = True
    random_state: int = 42
    # Hyperparameter search: "grid" | "random"
    search_type: str = "random"
    random_search_n_iter: int = 50
    # Class imbalance: "class_weight" | "smote" | "threshold" | "none"
    # Use class_weight by default (SMOTE can cause XGBoost sample_weight size mismatch)
    imbalance_strategy: str = "class_weight"
    smote_k_neighbors: int = 3
    # Cost-sensitive: multiply balanced weights for minority classes (down, no)
    minority_class_weight_multiplier: float = 2.5
    minority_classes: Tuple[str, ...] = ("down", "no")
    # Probability calibration (reduces overconfident predictions)
    # Disabled: caused models to collapse to majority classes (down/no recall → 0)
    use_calibration: bool = False
    calibration_cv: int = 3
    # Scoring for tuning (multiclass)
    scoring: str = "f1_weighted"
    n_jobs: int = -1


# Clinical cost matrix: cost[true][pred] = penalty for predicting pred when true is actual
# Rows=actual, Cols=predicted. Higher = worse. "up" predicted as "down" is dangerous (hypo risk).
CLINICAL_COST_MATRIX: Dict[str, Dict[str, float]] = {
    "down": {"down": 0, "up": 5, "steady": 1, "no": 1},   # down->up: severe (add insulin when should reduce)
    "up": {"down": 5, "up": 0, "steady": 1, "no": 1},     # up->down: severe (reduce when should add)
    "steady": {"down": 2, "up": 2, "steady": 0, "no": 0.5},
    "no": {"down": 3, "up": 2, "steady": 0.5, "no": 0},
}


@dataclass
class EvaluationConfig:
    """Configuration for model evaluation artifacts and analyses."""

    output_dir: Path = field(default_factory=lambda: Path("outputs/evaluation"))
    # Use clinical cost matrix for cost-sensitive evaluation
    use_clinical_cost: bool = True
    # Which plots to generate
    plot_confusion_matrix: bool = True
    plot_roc_auc_ovr: bool = True
    plot_calibration: bool = True
    plot_learning_curve: bool = True
    plot_feature_importance: bool = True
    # Learning curve settings
    learning_curve_train_sizes: Tuple[float, ...] = (0.1, 0.3, 0.5, 0.7, 1.0)
    # Permutation importance settings
    permutation_repeats: int = 10
    # Temporal validation
    temporal_segment_column: str = "temporal_segment"

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


@dataclass
class ExplainabilityConfig:
    """Configuration for SHAP-based explainability (Step 5)."""

    output_dir: Path = field(default_factory=lambda: Path("outputs/explainability"))
    # Background sample for KernelExplainer (None = use all train if small, else 100)
    background_size: int = 100
    # Global plots
    top_k_features: int = 10
    max_display_features: int = 15
    # Local explanations
    n_waterfall_samples: int = 5
    n_force_plot_samples: int = 3
    # Cohort / segment column for cohort-level analysis
    segment_column: str = "temporal_segment"
    # Clinical report
    feature_name_to_clinical: Optional[Dict[str, str]] = None  # set in code if needed
    similar_patients_k: int = 5

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


def _default_recommendation_content() -> Dict[str, Dict[str, Any]]:
    """Default ML class -> clinical recommendation content (person-first, collaborative CDS tone)."""
    return {
        "down": {
            "summary": "Consider a modest reduction in meal or correction insulin.",
            "action": "Decrease",
            "magnitude": "Moderate",
            "detail": "Based on the pattern entered, a lower dose may be reasonable. Review recent glucose trends and hypoglycemia risk with your care team before changing your plan.",
        },
        "up": {
            "summary": "Consider a modest increase in meal or correction insulin.",
            "action": "Increase",
            "magnitude": "Moderate",
            "detail": "Based on the pattern entered, a higher dose may be appropriate. Confirm against your glucose targets, ketone status, and sick-day rules before increasing.",
        },
        "steady": {
            "summary": "No change to basal or bolus plan is suggested from this snapshot.",
            "action": "Maintain",
            "magnitude": "None",
            "detail": "Continue your prescribed regimen and routine monitoring; bring persistent highs or lows to your clinician.",
        },
        "no": {
            "summary": "No structured insulin change is indicated from this assessment.",
            "action": "None",
            "magnitude": "None",
            "detail": "If symptoms or glucose readings change, repeat the assessment or contact your care team.",
        },
    }


@dataclass
class RecommendationConfig:
    """Configuration for the recommendation system (Step 6). Driven by ML model; content from config."""

    # Path to load the saved best model (InferenceBundle)
    best_model_dir: Path = field(default_factory=lambda: Path("outputs/best_model"))
    # ICR (insulin-to-carb ratio): 1 unit per X grams carbs. Used when patient doesn't provide.
    default_icr: float = 10.0
    # ISF (correction factor): 1 unit lowers BG by X mg/dL. Used when patient doesn't provide.
    default_isf: float = 50.0
    # Target glucose (mg/dL) for correction calculation
    target_glucose_mgdl: float = 100.0
    # Probability threshold below which to flag for clinician review (risk-aware)
    confidence_threshold: float = 0.75
    # CDS: confidence below this triggers "Requires Urgent Clinician Validation"
    cds_urgent_validation_threshold: float = 0.8
    # Max dose adjustment units (absolute) for safety
    max_adjustment: int = 5
    # IOB (insulin on board, mL) above this = significant; avoid stacking correction when BG high + trend down
    # U-100: 2 units = 0.02 mL
    iob_significant_threshold: float = 0.02
    # BG above this (mg/dL) = high; consider withholding correction if IOB significant and trend down
    glucose_high_for_stacking: float = 180.0
    # Entropy above this = high uncertainty, flag for review
    uncertainty_entropy_threshold: float = 1.0
    # Number of similar patients to include in explanations
    similar_patients_k: int = 5
    # Top K features to show in explanations
    top_k_features: int = 5
    # Optional: per-class probability thresholds (class_name -> min prob) for custom decision
    class_thresholds: Optional[Dict[str, float]] = None
    # Class -> recommendation content (summary, action, magnitude, detail); overridable for i18n/custom
    recommendation_content: Dict[str, Dict[str, Any]] = field(default_factory=_default_recommendation_content)


# ---------- Glucose Interpretation & Dosage Zones (standard reference) ----------

GLUCOSE_ZONES: List[Dict[str, Any]] = [
    {"id": "level2_hypo", "min_mg_dl": None, "max_mg_dl": GLUCOSE_LEVEL2_HYPO_MAX_MGDL, "label": "<54 mg/dL", "interpretation": "Level 2 Hypoglycemia", "action": f"Stop. Suspend all insulin logic. Consume {FAST_ACTING_CARBS_LEVEL2_GRAMS}g fast-acting carbs. Recheck in 15 min.", "severity": "critical"},
    {"id": "hypo", "min_mg_dl": GLUCOSE_LEVEL1_HYPO_MIN_MGDL, "max_mg_dl": GLUCOSE_HYPO_MAX_MGDL, "label": "54–69 mg/dL", "interpretation": "Level 1 Hypoglycemia", "action": f"Stop. Suspend all insulin logic. Consume {FAST_ACTING_CARBS_GRAMS}g fast-acting carbs. Recheck in 15 min.", "severity": "critical"},
    {"id": "low_normal", "min_mg_dl": GLUCOSE_LOW_NORMAL_MIN_MGDL, "max_mg_dl": GLUCOSE_LOW_NORMAL_MAX_MGDL, "label": "70 – 90", "interpretation": "Low-Normal", "action": "Dose for food only. Subtract from the meal bolus to prevent a dip.", "severity": "caution"},
    {"id": "target", "min_mg_dl": GLUCOSE_TARGET_MIN_MGDL, "max_mg_dl": GLUCOSE_TARGET_MAX_MGDL, "label": "90 – 130", "interpretation": "Target Range", "action": "Standard Dose. Apply Insulin-to-Carb Ratio only. No correction needed.", "severity": "normal"},
    {"id": "mild_hyper", "min_mg_dl": GLUCOSE_MILD_HYPER_MIN_MGDL, "max_mg_dl": GLUCOSE_MILD_HYPER_MAX_MGDL, "label": "131 – 180", "interpretation": "Mild Hyperglycemia", "action": "Apply Correction Factor (ISF) for the excess, but only if IOB is low.", "severity": "caution"},
    {"id": "moderate_high", "min_mg_dl": GLUCOSE_MODERATE_HIGH_MIN_MGDL, "max_mg_dl": GLUCOSE_MODERATE_HIGH_MAX_MGDL, "label": "181 – 250", "interpretation": "Moderate High", "action": "Add Correction Dose. Prompt user to check for hydration/stress factors.", "severity": "warning"},
    {"id": "severe_high", "min_mg_dl": GLUCOSE_SEVERE_HIGH_MIN_MGDL, "max_mg_dl": None, "label": "Above 250", "interpretation": "Severe High", "action": "Add Correction Dose. Urgent Alert: Check for Ketones if BG remains high for >2 hours.", "severity": "critical"},
]

# CDS Safety Engine categories (Level 1/2 hypo, target 70-180, hyper >180, critical >250 or high ketones)
GLUCOSE_CDS_CATEGORIES: List[Dict[str, Any]] = [
    {"id": "level2_hypoglycemia", "min_mg_dl": None, "max_mg_dl": GLUCOSE_LEVEL2_HYPO_MAX_MGDL, "label": "<54 mg/dL", "cds_category": "level2_hypoglycemia", "severity": "critical"},
    {"id": "level1_hypoglycemia", "min_mg_dl": GLUCOSE_LEVEL1_HYPO_MIN_MGDL, "max_mg_dl": GLUCOSE_LEVEL1_HYPO_MAX_MGDL, "label": "54–69 mg/dL", "cds_category": "level1_hypoglycemia", "severity": "critical"},
    {"id": "target_range", "min_mg_dl": GLUCOSE_CDS_TARGET_MIN_MGDL, "max_mg_dl": GLUCOSE_CDS_TARGET_MAX_MGDL, "label": "70–180 mg/dL", "cds_category": "target_range", "severity": "normal"},
    {"id": "hyperglycemia", "min_mg_dl": GLUCOSE_MODERATE_HIGH_MIN_MGDL, "max_mg_dl": GLUCOSE_MODERATE_HIGH_MAX_MGDL, "label": ">180 mg/dL", "cds_category": "hyperglycemia", "severity": "warning"},
    {"id": "critical_alert", "min_mg_dl": GLUCOSE_SEVERE_HIGH_MIN_MGDL, "max_mg_dl": None, "label": ">250 mg/dL", "cds_category": "critical_alert", "severity": "critical"},
]


def _glucose_label_from_zone(zone: Optional[Dict[str, Any]]) -> str:
    """Return display label for glucose (Low, High, Target, etc.)."""
    if not zone:
        return ""
    zid = zone.get("id", "")
    return {
        "hypo": "Low",
        "level2_hypo": "Low",
        "low_normal": "Low-Normal",
        "target": "Target",
        "mild_hyper": "Mild High",
        "moderate_high": "High",
        "severe_high": "Severe High",
    }.get(zid, "")


def _trend_display(trend: Optional[str]) -> str:
    """Map glucose_trend to UI display string."""
    if not trend or not str(trend).strip():
        return "—"
    t = str(trend).lower()
    return {"falling": "↘ Falling Slowly", "rising": "↗ Rising", "stable": "→ Stable"}.get(t, f"→ {t.title()}")


def get_glucose_zone_cds(glucose_mg_dl: Optional[float], ketone_high: bool = False) -> str:
    """Return CDS category: level2_hypoglycemia, level1_hypoglycemia, target_range, hyperglycemia, critical_alert."""
    if ketone_high:
        return "critical_alert"
    if glucose_mg_dl is None:
        return "target_range"
    try:
        gl = float(glucose_mg_dl)
    except (TypeError, ValueError):
        return "target_range"
    if gl <= GLUCOSE_LEVEL2_HYPO_MAX_MGDL:
        return "level2_hypoglycemia"
    if gl <= GLUCOSE_LEVEL1_HYPO_MAX_MGDL:
        return "level1_hypoglycemia"
    if gl <= GLUCOSE_CDS_TARGET_MAX_MGDL:
        return "target_range"
    if gl <= GLUCOSE_MODERATE_HIGH_MAX_MGDL:
        return "hyperglycemia"
    return "critical_alert"


def get_glucose_zone(glucose_mg_dl: float) -> Optional[Dict[str, Any]]:
    """Return the zone dict for a given glucose value, or None if invalid."""
    if glucose_mg_dl is None:
        return None
    try:
        gl = float(glucose_mg_dl)
    except (TypeError, ValueError):
        return None
    for z in GLUCOSE_ZONES:
        if z["min_mg_dl"] is not None and gl < z["min_mg_dl"]:
            continue
        if z["max_mg_dl"] is not None and gl > z["max_mg_dl"]:
            continue
        return z
    return None


@dataclass
class AlertConfig:
    """Thresholds for critical-condition alerts (no hardcoded values in routes)."""

    glucose_low_mg_dl: float = 70.0
    glucose_high_mg_dl: float = 400.0


@dataclass
class DashboardConfig:
    """Paths and settings for the visualization dashboard (Step 7)."""

    best_model_dir: Path = field(default_factory=lambda: Path("outputs/best_model"))
    #: Clinical insulin pipeline output dir (default ``outputs/clinical_insulin_pipeline/latest``).
    #: Set ``SMART_SENSOR_BUNDLE_DIR`` to override (name kept for compatibility).
    smart_sensor_bundle_dir: Path = field(default_factory=_default_smart_sensor_bundle_dir)
    evaluation_dir: Path = field(default_factory=lambda: Path("outputs/evaluation"))
    explainability_dir: Path = field(default_factory=lambda: Path("outputs/explainability"))
    recommendations_dir: Path = field(default_factory=lambda: Path("outputs/recommendations"))
    data_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[4] / "data" / "SmartSensor_DiabetesMonitoring.csv"
    )
    similar_patients_k: int = 5
