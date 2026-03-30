"""Paths and defaults for the clinical insulin pipeline."""
from __future__ import annotations

from pathlib import Path


def repo_root_from_here() -> Path:
    """clinical_insulin_pipeline lives under backend/src/."""
    return Path(__file__).resolve().parent.parent.parent.parent


DEFAULT_DATA_CSV = "data/SmartSensor_DiabetesMonitoring.csv"
OUTPUT_SUBDIR = "outputs/clinical_insulin_pipeline"
BUNDLE_FILENAME = "insulin_regression_bundle.joblib"
RANDOM_STATE = 42
TEST_SIZE = 0.2
KNN_NEIGHBORS_IMPUTER = 5
IQR_MULTIPLIER = 1.5
# Target: continuous meal/correction insulin (IU) in dataset; clip for training/inference consistency.
DOSE_MIN = 0.0
DOSE_MAX = 10.0
DOSE_ROUND_STEP = 0.5
# Target column in SmartSensor CSV (continuous IU)
TARGET_COL = "Insulin_Dose"
