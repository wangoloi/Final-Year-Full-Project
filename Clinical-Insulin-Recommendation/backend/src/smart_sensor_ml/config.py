"""Central configuration for the Smart Sensor ML pipeline."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Final, Tuple

RANDOM_STATE: Final[int] = 42
TEST_SIZE: Final[float] = 0.2
CV_FOLDS: Final[int] = 5
N_CLASSES: Final[int] = 3
CLASS_NAMES: Final[Tuple[str, ...]] = ("Low", "Moderate", "High")

# CSV columns (SmartSensor_DiabetesMonitoring.csv)
COL_PATIENT: Final[str] = "Patient_ID"
COL_TIME: Final[str] = "Timestamp"
# API / unified name (must match request body key after normalization)
COL_MEASUREMENT_TIME: Final[str] = "measurement_time"
COL_TARGET: Final[str] = "Insulin_Dose"
COL_IGNORE: Final[str] = "Predicted_Progression"

# Context fields (required at inference; synthesized for historical CSV rows)
COL_MEAL_CONTEXT: Final[str] = "meal_context"
COL_ACTIVITY_CONTEXT: Final[str] = "activity_context"

MEAL_CONTEXT_VALUES: Final[Tuple[str, ...]] = ("before_meal", "after_meal", "fasting")
ACTIVITY_CONTEXT_VALUES: Final[Tuple[str, ...]] = ("resting", "active", "post_exercise")

TIME_CATEGORIES: Final[Tuple[str, ...]] = ("morning", "afternoon", "evening", "night")

# Default training fill when CSV lacks context columns
DEFAULT_MEAL_CONTEXT: Final[str] = "fasting"
DEFAULT_ACTIVITY_CONTEXT: Final[str] = "resting"

NUMERIC_FEATURES: Final[Tuple[str, ...]] = (
    "Glucose_Level",
    "Heart_Rate",
    "Activity_Level",
    "Calories_Burned",
    "Sleep_Duration",
    "Step_Count",
    "Medication_Intake",
    "Diet_Quality_Score",
    "Stress_Level",
    "BMI",
    "HbA1c",
    "Blood_Pressure_Systolic",
    "Blood_Pressure_Diastolic",
)

# Composite model selection — rewards balanced, calibrated models
COMPOSITE_WEIGHTS: Final[Tuple[Tuple[str, float], ...]] = (
    ("f1_weighted", 0.30),
    ("roc_auc_ovr", 0.25),
    ("accuracy", 0.20),
    ("precision_weighted", 0.15),
    ("recall_weighted", 0.10),
)

# Tie-break: if top-two composite within this gap, prefer lower CV std / smaller train–val gap
COMPOSITE_TIE_THRESHOLD: Final[float] = 0.02

# Feature selection (train-only MI); pool size for correlation filter; final N chosen on validation
MI_MAX_POOL_FOR_CORR: Final[int] = 60
MI_MIN_FEATURES: Final[int] = 8
MI_MAX_FEATURES: Final[int] = 64
# Candidate feature counts (validation pick); env override: comma-separated
FEATURE_COUNT_CANDIDATES: Final[Tuple[int, ...]] = tuple(
    int(x.strip()) for x in os.environ.get("SMART_SENSOR_FEATURE_COUNTS", "10,20,30,40,50").split(",") if x.strip()
) or (10, 20, 30, 40, 50)

# Hyperparameter search (grouped CV); override with env SMART_SENSOR_TUNING_N_ITER for speed
TUNING_N_ITER: Final[int] = int(os.environ.get("SMART_SENSOR_TUNING_N_ITER", "24"))
TUNING_CV_FOLDS: Final[int] = int(os.environ.get("SMART_SENSOR_TUNING_CV_FOLDS", "5"))

# Generalized evaluation score (reporting only; selection still uses validation R² + gap rule)
# GES = w_tr·R²_train + w_val·R²_val + w_te·R²_test − w_gap·max(0, train−val gap)
EVAL_GENERALIZED_WEIGHT_TRAIN: Final[float] = 0.15
EVAL_GENERALIZED_WEIGHT_VAL: Final[float] = 0.425
EVAL_GENERALIZED_WEIGHT_TEST: Final[float] = 0.425
EVAL_GENERALIZED_GAP_PENALTY: Final[float] = 0.25

# Row-wise derived numeric features (no leakage — per-row algebra only)
DERIVED_FEATURE_NAMES: Final[Tuple[str, ...]] = (
    "glucose_bmi_ratio",
    "glucose_hba1c_product",
    "hr_glucose_ratio",
    "activity_glucose_interaction",
    "pulse_pressure",
    "steps_per_sleep_hour",
    "map_approx",
)


def default_data_path(repo_root: Path | None = None) -> Path:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "SmartSensor_DiabetesMonitoring.csv"


def default_output_dir(repo_root: Path | None = None) -> Path:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "outputs" / "smart_sensor_ml"


def default_bundle_path(repo_root: Path | None = None) -> Path:
    """Single joblib bundle for deployment (§11, §16)."""
    return default_output_dir(repo_root) / "model_bundle" / "bundle.joblib"
