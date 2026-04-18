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

    # Interaction terms and non-linear features to boost signal.
    out["Glucose_Activity_Interaction"] = g * act
    out["Metabolic_Index"] = h * g
    out["HbA1c_Squared"] = h ** 2
    out["Glucose_Squared"] = g ** 2
    return out


def _time_of_day_label(hour: int) -> str:
    if hour < 6:
        return "Night"
    if hour < 12:
        return "Morning"
    if hour < 18:
        return "Afternoon"
    return "Evening"


def add_time_series_features(
    df: pd.DataFrame,
    ts_col: str = "Timestamp",
    patient_col: str = "Patient_ID",
) -> pd.DataFrame:
    out = df.copy()
    out[ts_col] = pd.to_datetime(out[ts_col], errors="coerce")
    out = out.sort_values([patient_col, ts_col]).reset_index(drop=True)

    out["time_since_prev_min"] = (
        out.groupby(patient_col)[ts_col]
        .diff()
        .dt.total_seconds()
        .div(60)
        .fillna(0.0)
    )
    out["glucose_previous"] = out.groupby(patient_col)["Glucose_Level"].shift(1)
    out["glucose_momentum"] = out["Glucose_Level"] - out["glucose_previous"]
    out["insulin_previous"] = out.groupby(patient_col)["Insulin_Dose"].shift(1)
    out["time_of_day_category"] = out[ts_col].dt.hour.map(_time_of_day_label).fillna("Unknown")

    for window, name in [("3h", "glucose_roll_3h"), ("24h", "glucose_roll_24h")]:
        out[name] = (
            out.groupby(patient_col)
            .apply(lambda g: g.set_index(ts_col)["Glucose_Level"].rolling(window).mean())
            .reset_index(level=0, drop=True)
        )

    for window, name in [("3h", "insulin_roll_3h"), ("24h", "insulin_roll_24h")]:
        out[name] = (
            out.groupby(patient_col)
            .apply(lambda g: g.set_index(ts_col)["Insulin_Dose"].rolling(window).mean())
            .reset_index(level=0, drop=True)
        )

    out["glucose_previous"] = out["glucose_previous"].fillna(out["Glucose_Level"])
    out["glucose_momentum"] = out["glucose_momentum"].fillna(0.0)
    out["time_since_prev_min"] = out["time_since_prev_min"].fillna(0.0)
    out["insulin_previous"] = out["insulin_previous"].fillna(0.0)
    out["glucose_roll_3h"] = out["glucose_roll_3h"].fillna(out["Glucose_Level"])
    out["glucose_roll_24h"] = out["glucose_roll_24h"].fillna(out["Glucose_Level"])
    out["insulin_roll_3h"] = out["insulin_roll_3h"].fillna(0.0)
    out["insulin_roll_24h"] = out["insulin_roll_24h"].fillna(0.0)
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
        "Glucose_Activity_Interaction",
        "Metabolic_Index",
        "HbA1c_Squared",
        "Glucose_Squared",
        "time_since_prev_min",
        "glucose_previous",
        "glucose_momentum",
        "glucose_roll_3h",
        "glucose_roll_24h",
        "insulin_previous",
        "insulin_roll_3h",
        "insulin_roll_24h",
        "time_of_day_category",
    ]
