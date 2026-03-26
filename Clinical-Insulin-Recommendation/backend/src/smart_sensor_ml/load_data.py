"""1. Input layer — load CSV and enrich for Smart Sensor pipeline."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def load_data(csv_path: Path) -> pd.DataFrame:
    """
    Load the Smart Sensor dataset from CSV.

    Returns:
        Raw DataFrame (column names as in file).
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path)
    logger.info("Loaded %s rows, %s columns from %s", len(df), len(df.columns), path)
    return df


def enrich_training_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure meal_context, activity_context, and measurement_time exist for training.

    Historical SmartSensor CSV may omit context columns; use defaults (spec: defaults for
    rows without API-provided context).
    """
    out = df.copy()
    if config.COL_MEAL_CONTEXT not in out.columns:
        out[config.COL_MEAL_CONTEXT] = config.DEFAULT_MEAL_CONTEXT
        logger.info("Added %s=%r for all rows (CSV had no column)", config.COL_MEAL_CONTEXT, config.DEFAULT_MEAL_CONTEXT)
    else:
        out[config.COL_MEAL_CONTEXT] = out[config.COL_MEAL_CONTEXT].fillna(config.DEFAULT_MEAL_CONTEXT)
    if config.COL_ACTIVITY_CONTEXT not in out.columns:
        out[config.COL_ACTIVITY_CONTEXT] = config.DEFAULT_ACTIVITY_CONTEXT
        logger.info("Added %s=%r for all rows (CSV had no column)", config.COL_ACTIVITY_CONTEXT, config.DEFAULT_ACTIVITY_CONTEXT)
    else:
        out[config.COL_ACTIVITY_CONTEXT] = out[config.COL_ACTIVITY_CONTEXT].fillna(config.DEFAULT_ACTIVITY_CONTEXT)

    for col in (config.COL_MEAL_CONTEXT, config.COL_ACTIVITY_CONTEXT):
        out[col] = out[col].astype(str).str.strip().str.lower()
        # normalize common variants
        out[col] = out[col].replace({"": config.DEFAULT_MEAL_CONTEXT if col == config.COL_MEAL_CONTEXT else config.DEFAULT_ACTIVITY_CONTEXT})

    if config.COL_MEASUREMENT_TIME not in out.columns:
        out[config.COL_MEASUREMENT_TIME] = out[config.COL_TIME]
    else:
        out[config.COL_MEASUREMENT_TIME] = out[config.COL_MEASUREMENT_TIME].fillna(out[config.COL_TIME])

    return out


def exploratory_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Initial exploratory checks: shape, dtypes, missing counts, basic describe()."""
    missing = df.isna().sum()
    return {
        "head": df.head(5),
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing_per_column": missing[missing > 0].to_dict() if missing.any() else {},
        "missing_total": int(missing.sum()),
        "describe_numeric": df.select_dtypes(include="number").describe().to_dict(),
    }


def print_exploratory(summary: Dict[str, Any]) -> None:
    """Human-readable EDA for logs / notebooks."""
    print("=== First 5 rows ===")
    print(summary["head"])
    print("\n=== Shape ===", summary["shape"])
    print("\n=== Column names ===", summary["columns"])
    print("\n=== Data types ===")
    for k, v in summary["dtypes"].items():
        print(f"  {k}: {v}")
    print("\n=== Missing values ===", summary["missing_per_column"] or "none")
    print("\n=== Numeric describe (subset) ===")
    desc = summary.get("describe_numeric") or {}
    if desc:
        print(pd.DataFrame(desc).round(3))
