"""Consolidated train / validation / test metrics + generalized score; written after pipeline run."""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def _safe_float(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def generalized_evaluation_score(
    r2_train: float,
    r2_val: float,
    r2_test: float,
    overfit_gap_r2_train_val: float,
) -> float:
    """
    Single summary that uses **all three splits** (not test-only):
    emphasizes validation + test generalization, nudges with train signal,
    penalizes train≫val (overfitting). For **reporting**; model selection stays val-based.
    """
    gap = max(0.0, float(overfit_gap_r2_train_val))
    return (
        config.EVAL_GENERALIZED_WEIGHT_TRAIN * float(r2_train)
        + config.EVAL_GENERALIZED_WEIGHT_VAL * float(r2_val)
        + config.EVAL_GENERALIZED_WEIGHT_TEST * float(r2_test)
        - config.EVAL_GENERALIZED_GAP_PENALTY * gap
    )


def enrich_comparison_with_generalized_score(comp: pd.DataFrame) -> pd.DataFrame:
    out = comp.copy()
    out["generalized_evaluation_score"] = [
        generalized_evaluation_score(
            float(r["train_r2"]),
            float(r["val_r2"]),
            float(r["test_r2"]),
            float(r["overfit_gap_r2_train_val"]),
        )
        for _, r in out.iterrows()
    ]
    return out


def build_evaluation_report(
    comp: pd.DataFrame,
    best_model_name: str,
    selection_rule: str,
    out_dir: Path,
    bundle_dir: Path,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Structured report: every model with train/val/test metrics + best model + deployment hints."""
    repo_root = repo_root or Path(__file__).resolve().parents[3]
    out_dir = Path(out_dir).resolve()
    bundle_dir = Path(bundle_dir).resolve()
    bundle_joblib = bundle_dir / "bundle.joblib"
    meta_json = bundle_dir / "metadata.json"

    comp_enriched = (
        comp
        if "generalized_evaluation_score" in comp.columns
        else enrich_comparison_with_generalized_score(comp)
    )
    models: List[Dict[str, Any]] = []
    for _, r in comp_enriched.iterrows():
        models.append(
            {
                "model": str(r["model"]),
                "metrics": {
                    "train": {
                        "r2": float(r["train_r2"]),
                        "rmse": float(r["train_rmse"]),
                        "mae": _safe_float(r.get("train_mae")),
                    },
                    "validation": {
                        "r2": float(r["val_r2"]),
                        "rmse": float(r["val_rmse"]),
                        "mae": float(r["val_mae"]),
                    },
                    "test": {
                        "r2": float(r["test_r2"]),
                        "rmse": float(r["test_rmse"]),
                        "mae": float(r["test_mae"]),
                    },
                },
                "train_val_gap_r2": float(r["overfit_gap_r2_train_val"]),
                "generalized_evaluation_score": float(r["generalized_evaluation_score"]),
            }
        )

    models_by_val = sorted(models, key=lambda m: m["metrics"]["validation"]["r2"], reverse=True)
    models_by_ges = sorted(models, key=lambda m: m["generalized_evaluation_score"], reverse=True)

    best = next(m for m in models if m["model"] == best_model_name)

    try:
        rel_bundle = str(bundle_dir.relative_to(repo_root.resolve()))
    except ValueError:
        rel_bundle = str(bundle_dir)

    report: Dict[str, Any] = {
        "version": 1,
        "task": "regression",
        "selection": {
            "primary_rule": selection_rule,
            "best_model_for_deployment": best_model_name,
            "same_as_saved_bundle": True,
            "note": "The saved bundle.joblib contains this exact estimator + preprocessor.",
        },
        "generalized_evaluation_score": {
            "name": "GES",
            "formula": (
                f"{config.EVAL_GENERALIZED_WEIGHT_TRAIN}·R²_train + "
                f"{config.EVAL_GENERALIZED_WEIGHT_VAL}·R²_val + "
                f"{config.EVAL_GENERALIZED_WEIGHT_TEST}·R²_test − "
                f"{config.EVAL_GENERALIZED_GAP_PENALTY}·max(0, train_val_gap_r2)"
            ),
            "purpose": "Summarize all splits in one number for dashboards; selection still uses validation-led rule.",
            "best_model_score": best["generalized_evaluation_score"],
        },
        "best_model": {
            "name": best_model_name,
            "metrics": best["metrics"],
            "train_val_gap_r2": best["train_val_gap_r2"],
            "generalized_evaluation_score": best["generalized_evaluation_score"],
        },
        "models_ranked_by_validation_r2": models_by_val,
        "models_ranked_by_generalized_score": models_by_ges,
        "deployment": {
            "bundle_directory": str(bundle_dir),
            "bundle_joblib": str(bundle_joblib),
            "metadata_json": str(meta_json),
            "bundle_directory_repo_relative": rel_bundle,
            "api_default_bundle_dir": "outputs/smart_sensor_ml/model_bundle",
            "how_to_load_this_run": (
                "Set environment variable SMART_SENSOR_BUNDLE_DIR to the bundle_directory above, "
                "or copy bundle.joblib, metadata.json, and shap_background.npy into outputs/smart_sensor_ml/model_bundle "
                "relative to the Clinical-Insulin-Recommendation repo when starting the API."
            ),
        },
    }
    return report


def write_evaluation_report(report: Dict[str, Any], out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Wrote evaluation report: %s", out_path)


def best_model_metrics_nested(best_row: pd.Series) -> Dict[str, Dict[str, Any]]:
    """For metadata.json — nested train/val/test numbers for the chosen model."""
    return {
        "train": {
            "r2": float(best_row["train_r2"]),
            "rmse": float(best_row["train_rmse"]),
            "mae": _safe_float(best_row.get("train_mae")),
        },
        "validation": {
            "r2": float(best_row["val_r2"]),
            "rmse": float(best_row["val_rmse"]),
            "mae": float(best_row["val_mae"]),
        },
        "test": {
            "r2": float(best_row["test_r2"]),
            "rmse": float(best_row["test_rmse"]),
            "mae": float(best_row["test_mae"]),
        },
    }
