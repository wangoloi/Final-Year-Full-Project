"""2. Data validation — schema, ranges, duplicates."""
from __future__ import annotations

import logging
import warnings
from typing import List, Tuple

import numpy as np
import pandas as pd

from smart_sensor_ml import config

logger = logging.getLogger(__name__)

# Domain-inspired bounds (soft checks — warn, do not drop by default here)
BOUNDS = {
    "Glucose_Level": (40.0, 500.0),
    "Heart_Rate": (30.0, 220.0),
    "BMI": (12.0, 60.0),
    "HbA1c": (4.0, 15.0),
    "Blood_Pressure_Systolic": (70.0, 250.0),
    "Blood_Pressure_Diastolic": (40.0, 150.0),
    "Insulin_Dose": (0.0, 100.0),
    "Sleep_Duration": (0.0, 24.0),
    "Stress_Level": (0.0, 10.0),
    "Diet_Quality_Score": (0.0, 10.0),
}


def validate_data(df: pd.DataFrame, fix_duplicates: bool = True) -> Tuple[pd.DataFrame, List[str]]:
    """
    Validate dataset; return possibly cleaned frame and list of warning messages.

    Checks:
      - required columns
      - missing / null summary
      - duplicate rows (optional drop)
      - numeric domain ranges (warnings)
      - Patient_ID consistency (no empty)
    """
    msgs: List[str] = []
    required = [
        config.COL_PATIENT,
        config.COL_TIME,
        config.COL_TARGET,
        config.COL_MEASUREMENT_TIME,
        config.COL_MEAL_CONTEXT,
        config.COL_ACTIVITY_CONTEXT,
    ] + list(config.NUMERIC_FEATURES)
    missing_cols = set(required) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

    if df[config.COL_PATIENT].astype(str).str.strip().eq("").any():
        msgs.append("Empty Patient_ID values found.")

    dup = df.duplicated().sum()
    if dup:
        msgs.append(f"Duplicate rows: {dup}.")
        if fix_duplicates:
            df = df.drop_duplicates().reset_index(drop=True)
            msgs.append("Dropped duplicate rows.")

    for col, (lo, hi) in BOUNDS.items():
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        bad = ((s < lo) | (s > hi)) & s.notna()
        n_bad = int(bad.sum())
        if n_bad:
            warnings.warn(f"{col}: {n_bad} values outside typical range [{lo}, {hi}].")
            msgs.append(f"{col}: {n_bad} values outside [{lo}, {hi}] (warning only).")

    logger.info("Validation finished with %s messages", len(msgs))
    return df, msgs
