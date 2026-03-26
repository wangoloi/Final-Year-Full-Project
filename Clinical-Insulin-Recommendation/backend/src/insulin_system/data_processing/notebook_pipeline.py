"""
Notebook-based pipeline: replicates the preprocessing and training logic from
insulin_prediction_development.ipynb for use in run_notebook_pipeline.py.

Flow: Load -> LabelEncode categoricals -> MI feature selection -> StandardScaler
      -> 80/10/10 stratified split -> Train models.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from sklearn.feature_selection import mutual_info_classif
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ..config.schema import DataSchema
from .load import load_and_validate

logger = logging.getLogger(__name__)

RANDOM_STATE = 42
TOP_K = 15


@dataclass
class NotebookPipelineResult:
    """Result of running the notebook-style pipeline."""

    X_train: np.ndarray
    X_val: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray
    y_val: np.ndarray
    y_test: np.ndarray
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    feature_names: List[str] = field(default_factory=list)
    label_encoders: Dict[str, LabelEncoder] = field(default_factory=dict)
    scaler: Optional[StandardScaler] = None
    target_encoder: Optional[LabelEncoder] = None


def fit_label_encoders(df: pd.DataFrame, cols: List[str]) -> Dict[str, LabelEncoder]:
    """Fit LabelEncoders for categorical columns (notebook logic)."""
    encoders: Dict[str, LabelEncoder] = {}
    for col in cols:
        if col in df.columns:
            le = LabelEncoder()
            le.fit(df[col].astype(str))
            encoders[col] = le
    return encoders


def transform_with_encoders(df: pd.DataFrame, encoders: Dict[str, LabelEncoder]) -> pd.DataFrame:
    """Transform categorical columns using fitted encoders (notebook logic)."""
    out = df.copy()
    for col, le in encoders.items():
        if col in out.columns:
            out[col] = le.transform(out[col].astype(str))
    return out


def run_notebook_pipeline(
    data_path: Path,
    top_k: int = TOP_K,
    random_state: int = RANDOM_STATE,
) -> NotebookPipelineResult:
    """
    Run the notebook's preprocessing and split logic.
    Returns train/val/test arrays and fitted components.
    """
    schema = DataSchema()
    df = load_and_validate(data_path)

    # Encode categoricals (notebook: LabelEncoder per column)
    cat_cols = [c for c in schema.CATEGORICAL if c in df.columns]
    label_encoders = fit_label_encoders(df, cat_cols)
    df_encoded = transform_with_encoders(df, label_encoders)

    # Target encoder (for inverse transform at inference)
    target_col = schema.TARGET
    target_encoder = LabelEncoder()
    target_encoder.fit(df_encoded[target_col].astype(str))
    df_encoded[target_col] = target_encoder.transform(df_encoded[target_col].astype(str))
    label_encoders[target_col] = target_encoder

    # Feature selection: mutual information (notebook logic)
    feature_cols = [
        c for c in df_encoded.columns
        if c not in (schema.TARGET, schema.PATIENT_ID)
    ]
    X = df_encoded[feature_cols]
    y = df_encoded[target_col].values

    mi_scores = mutual_info_classif(X, y, random_state=random_state)
    mi_df = pd.DataFrame({"feature": feature_cols, "mi_score": mi_scores})
    mi_df = mi_df.sort_values("mi_score", ascending=False)
    selected_features = mi_df.head(min(top_k, len(feature_cols)))["feature"].tolist()

    X_selected = X[selected_features]

    # Split: 80/10/10 stratified (notebook logic)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_selected, y,
        test_size=0.1,
        random_state=random_state,
        stratify=y,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp,
        test_size=1 / 9,
        random_state=random_state,
        stratify=y_temp,
    )

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # DataFrames for reference (indices from split)
    train_df = df.loc[X_train.index].copy() if hasattr(X_train, "index") else pd.DataFrame()
    val_df = df.loc[X_val.index].copy() if hasattr(X_val, "index") else pd.DataFrame()
    test_df = df.loc[X_test.index].copy() if hasattr(X_test, "index") else pd.DataFrame()

    logger.info(
        "Notebook pipeline: train=%s val=%s test=%s features=%s",
        len(X_train), len(X_val), len(X_test), len(selected_features),
    )

    return NotebookPipelineResult(
        X_train=X_train_scaled,
        X_val=X_val_scaled,
        X_test=X_test_scaled,
        y_train=y_train,
        y_val=y_val,
        y_test=y_test,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        feature_names=selected_features,
        label_encoders=label_encoders,
        scaler=scaler,
        target_encoder=target_encoder,
    )
