"""Cyclical time features and clinically motivated derived columns."""
from __future__ import annotations

import math
from typing import List

import numpy as np
import pandas as pd


def add_cyclical_time_features(df: pd.DataFrame, ts_col: str = "Timestamp") -> pd.DataFrame:
    """Add hour, day-of-week, month and sin/cos encodings (Timestamp column required)."""
    out = df.copy()
    ts = pd.to_datetime(out[ts_col], errors="coerce")
    out["hour"] = ts.dt.hour.fillna(0).astype(int)
    out["day_of_week"] = ts.dt.dayofweek.fillna(0).astype(int)
    out["month"] = ts.dt.month.fillna(1).astype(int)

    out["hour_sin"] = np.sin(2 * math.pi * out["hour"] / 24.0)
    out["hour_cos"] = np.cos(2 * math.pi * out["hour"] / 24.0)
    out["month_sin"] = np.sin(2 * math.pi * (out["month"] - 1) / 12.0)
    out["month_cos"] = np.cos(2 * math.pi * (out["month"] - 1) / 12.0)
    out["dow_sin"] = np.sin(2 * math.pi * out["day_of_week"] / 7.0)
    out["dow_cos"] = np.cos(2 * math.pi * out["day_of_week"] / 7.0)
    return out


def add_derived_clinical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Domain-motivated terms (no target leakage).
    Excludes Predicted_Progression — often another model output and risks leakage.
    """
    out = df.copy()
    g = out["Glucose_Level"].astype(float)
    h = out["HbA1c"].astype(float)
    sys_bp = out["Blood_Pressure_Systolic"].astype(float)
    dia_bp = out["Blood_Pressure_Diastolic"].astype(float)
    act = out["Activity_Level"].astype(float)
    steps = out["Step_Count"].astype(float)

    out["glycemic_stress_index"] = (g * h) / 100.0
    out["pulse_pressure"] = sys_bp - dia_bp
    out["activity_volume"] = act * np.log1p(np.maximum(steps, 0.0))
    return out


def feature_columns_after_engineering() -> List[str]:
    """Ordered feature columns for modeling (Patient_ID and raw Timestamp excluded)."""
    return [
        "hour_sin",
        "hour_cos",
        "month_sin",
        "month_cos",
        "dow_sin",
        "dow_cos",
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
        "glycemic_stress_index",
        "pulse_pressure",
        "activity_volume",
    ]
