"""Load CSV, IQR outlier filtering, group-wise train/test split."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from ..config import DOSE_MAX, DOSE_MIN, IQR_MULTIPLIER, RANDOM_STATE, TARGET_COL, TEST_SIZE
from .features import (
    add_cyclical_time_features,
    add_derived_clinical_features,
    feature_columns_after_engineering,
)


PATIENT_COL = "Patient_ID"
TS_COL = "Timestamp"


def _iqr_mask(s: pd.Series) -> pd.Series:
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lo = q1 - IQR_MULTIPLIER * iqr
    hi = q3 + IQR_MULTIPLIER * iqr
    return (s >= lo) & (s <= hi)


def load_raw_csv(path: Path) -> pd.DataFrame:
    """Python engine avoids rare pandas C-parser failures on some Windows/Python builds."""
    return pd.read_csv(path, engine="python", encoding="utf-8")


def build_modeling_frame(
    df: pd.DataFrame,
    *,
    apply_iqr: bool = True,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, int]:
    """
    Returns:
      X_frame: features only (no Patient_ID)
      y: target
      groups: Patient_ID aligned with rows (for metadata / per-patient analysis)
      n_rows_dropped_iqr: count of rows removed by IQR on BMI + BP
    """
    df = add_cyclical_time_features(df, TS_COL)
    df = add_derived_clinical_features(df)
    n_before = len(df)
    if apply_iqr:
        m = np.ones(len(df), dtype=bool)
        for col in ("BMI", "Blood_Pressure_Systolic", "Blood_Pressure_Diastolic"):
            if col in df.columns:
                m &= _iqr_mask(df[col].astype(float))
        df = df.loc[m].reset_index(drop=True)
    n_drop = n_before - len(df)

    cols = feature_columns_after_engineering()
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns after engineering: {missing}")

    X = df[cols].copy()
    y = df[TARGET_COL].astype(float).clip(DOSE_MIN, DOSE_MAX)
    groups = df[PATIENT_COL].astype(str)
    return X, y, groups, n_drop


def train_test_group_split(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    test_size: float = TEST_SIZE,
    random_state: int = RANDOM_STATE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, np.ndarray, np.ndarray]:
    """Group-wise holdout: no patient appears in both train and test."""
    gss = GroupShuffleSplit(n_splits=5, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    g_train = groups.iloc[train_idx].values
    g_test = groups.iloc[test_idx].values
    return X_train, X_test, y_train, y_test, g_train, g_test


@dataclass
class DatasetBundle:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    groups_train: np.ndarray
    groups_test: np.ndarray
    feature_names: list[str]
    n_rows_dropped_iqr: int


def prepare_dataset(csv_path: Path, *, apply_iqr: bool = True) -> DatasetBundle:
    df = load_raw_csv(csv_path)
    X, y, groups, n_drop = build_modeling_frame(df, apply_iqr=apply_iqr)
    X_train, X_test, y_train, y_test, g_tr, g_te = train_test_group_split(X, y, groups)
    return DatasetBundle(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        groups_train=g_tr,
        groups_test=g_te,
        feature_names=list(X.columns),
        n_rows_dropped_iqr=n_drop,
    )
