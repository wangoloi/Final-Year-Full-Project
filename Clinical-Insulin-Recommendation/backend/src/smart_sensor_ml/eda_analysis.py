"""Exploratory data analysis for Smart Sensor insulin dose (regression) — runs before modeling."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def _skew(x: pd.Series) -> float:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if len(x) < 3:
        return float("nan")
    return float(x.skew())


def run_full_eda(df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
    """
    Full EDA: structure, missingness, target distribution, correlations, duplicates.
    Writes eda/eda_summary.json, eda/correlations_with_target.csv, eda/feature_summary.csv.
    """
    out_dir = Path(out_dir) / "eda"
    out_dir.mkdir(parents=True, exist_ok=True)

    y = pd.to_numeric(df[config.COL_TARGET], errors="coerce")

    missing = df.isna().sum()
    n_dup = int(df.duplicated().sum())

    target_stats = {
        "count_non_null": int(y.notna().sum()),
        "mean": float(y.mean()) if y.notna().any() else None,
        "std": float(y.std()) if y.notna().any() else None,
        "min": float(y.min()) if y.notna().any() else None,
        "max": float(y.max()) if y.notna().any() else None,
        "skewness": _skew(y),
        "quantiles": {str(q): float(y.quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)} if y.notna().any() else {},
    }

    # Per-column: unique counts, nunique for categoricals
    col_info: List[Dict[str, Any]] = []
    for c in df.columns:
        if c == config.COL_IGNORE:
            continue
        s = df[c]
        col_info.append(
            {
                "column": c,
                "dtype": str(s.dtype),
                "missing_count": int(s.isna().sum()),
                "n_unique": int(s.nunique(dropna=True)),
            }
        )

    # Correlation with target (numeric columns only)
    corr_rows: List[Dict[str, Any]] = []
    yv = y.values.astype(float)
    for c in df.columns:
        if c in (config.COL_TARGET, config.COL_IGNORE, config.COL_PATIENT):
            continue
        if df[c].dtype == object:
            continue
        xv = pd.to_numeric(df[c], errors="coerce").values
        mask = np.isfinite(xv) & np.isfinite(yv)
        if mask.sum() < 30:
            continue
        r = float(np.corrcoef(xv[mask], yv[mask])[0, 1])
        corr_rows.append({"feature": c, "pearson_r_with_insulin_dose": r})

    corr_df = pd.DataFrame(corr_rows).sort_values("pearson_r_with_insulin_dose", key=np.abs, ascending=False)
    corr_df.to_csv(out_dir / "correlations_with_target.csv", index=False)

    # Patient-level: median dose spread
    patient_med = df.groupby(config.COL_PATIENT, sort=False)[config.COL_TARGET].apply(
        lambda s: pd.to_numeric(s, errors="coerce").median()
    )
    patient_summary = {
        "n_patients": int(df[config.COL_PATIENT].nunique()),
        "median_of_patient_medians": float(patient_med.median()) if len(patient_med) else None,
        "std_of_patient_medians": float(patient_med.std()) if len(patient_med) > 1 else None,
    }

    summary: Dict[str, Any] = {
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "column_names": list(df.columns),
        "duplicate_rows": n_dup,
        "missing_total": int(missing.sum()),
        "missing_by_column": missing[missing > 0].to_dict() if missing.any() else {},
        "target_insulin_dose": target_stats,
        "patient_level": patient_summary,
        "columns": col_info,
        "top_correlations_with_target": corr_df.head(20).to_dict(orient="records"),
    }

    with open(out_dir / "eda_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    pd.DataFrame(col_info).to_csv(out_dir / "feature_summary.csv", index=False)

    logger.info("EDA written to %s (eda_summary.json, correlations_with_target.csv)", out_dir)
    return summary


def plot_eda_figures(df: pd.DataFrame, out_dir: Path) -> None:
    """Optional charts: insulin distribution, glucose vs dose scatter, correlation heatmap (numeric subset)."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    out_dir = Path(out_dir) / "eda"
    out_dir.mkdir(parents=True, exist_ok=True)

    y = pd.to_numeric(df[config.COL_TARGET], errors="coerce")
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.histplot(y.dropna(), kde=True, ax=ax)
    ax.set_title("Insulin dose (target) distribution")
    fig.tight_layout()
    fig.savefig(out_dir / "target_insulin_distribution.png", dpi=150)
    plt.close(fig)

    g = pd.to_numeric(df.get("Glucose_Level"), errors="coerce")
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.scatterplot(x=g, y=y, alpha=0.15, ax=ax)
    ax.set_xlabel("Glucose_Level")
    ax.set_ylabel("Insulin_Dose")
    ax.set_title("Glucose vs insulin dose (row-level)")
    fig.tight_layout()
    fig.savefig(out_dir / "glucose_vs_insulin.png", dpi=150)
    plt.close(fig)

    num = df.select_dtypes(include=[np.number]).copy()
    if len(num.columns) >= 3:
        # small numeric heatmap (limit columns)
        cols = [c for c in num.columns if c != config.COL_IGNORE][:15]
        if len(cols) >= 2:
            cm = num[cols].corr()
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(cm, annot=False, cmap="vlag", center=0, ax=ax)
            ax.set_title("Numeric feature correlation matrix (subset)")
            fig.tight_layout()
            fig.savefig(out_dir / "correlation_heatmap_numeric.png", dpi=120)
            plt.close(fig)
