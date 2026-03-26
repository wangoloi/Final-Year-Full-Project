"""
Deploy best model from existing experiment table using multi-objective selection.

Use this when you have run experiments and want to re-select the best model
using the updated multi-objective scoring (instead of clinical_cost alone),
then retrain and deploy without re-running the full pipeline.

Usage:
  python scripts/deploy_best_from_experiments.py
  python scripts/deploy_best_from_experiments.py --table outputs/clinical_ml_experiments/experiment_table.csv
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import pandas as pd

from clinical_ml_pipeline.config import select_best_row_by_rank
from insulin_system.config.schema import PipelineConfig
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.persistence import InferenceBundle, save_best_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_and_select_best(table_path: Path) -> dict:
    """Load experiment table, select best by rank-based (Borda-style) scoring."""
    df = pd.read_csv(table_path)
    if df.empty:
        raise ValueError(f"No experiments in {table_path}")

    # Exclude ensemble rows for single-model deploy (or include if desired)
    single = df[~df["model"].isin(["ensemble_stacking", "ensemble_soft_voting"])].copy()
    if single.empty:
        single = df

    best_row = select_best_row_by_rank(single)
    best = best_row.to_dict()
    logger.info(
        "Selected best (rank-based): %s (%s, %s) total_rank=%.1f f1=%.4f cost=%.4f",
        best["model"], best.get("imbalance_strategy", "?"), best.get("calibration_method", "none"),
        best.get("_total_rank", 0), best["f1_weighted"], best["clinical_cost"],
    )
    return best


def _parse_hyperparams(hyperparams_json: str) -> dict:
    """Parse hyperparameters, excluding calibration key."""
    try:
        params = json.loads(hyperparams_json.replace("'", '"'))
    except Exception:
        params = {}
    params.pop("calibration", None)
    return params


def main(
    table_path: Path | None = None,
    data_path: Path | None = None,
    best_model_dir: Path | None = None,
    output_dir: Path | None = None,
    use_patient_split: bool = False,
) -> int:
    if table_path is None:
        table_path = REPO_ROOT / "outputs/clinical_ml_experiments/experiment_table.csv"
    if data_path is None:
        data_path = REPO_ROOT / "data" / "SmartSensor_DiabetesMonitoring.csv"
    if best_model_dir is None:
        best_model_dir = REPO_ROOT / "outputs/best_model"
    if output_dir is None:
        output_dir = REPO_ROOT / "outputs/clinical_ml_experiments"
    if not table_path.exists():
        logger.error("Experiment table not found: %s. Run the pipeline first.", table_path)
        return 1
    if not data_path.exists():
        logger.error("Data not found: %s", data_path)
        return 1

    best = _load_and_select_best(table_path)
    model_name = best["model"]
    imb = best.get("imbalance_strategy", "class_weight")
    cal_method = best.get("calibration_method", "none")
    params = _parse_hyperparams(str(best.get("hyperparameters", "{}")))

    logger.info("Running data pipeline...")
    split_type = "patient" if use_patient_split else "random"
    pipe_config = PipelineConfig(split_type=split_type)
    pipeline = DataProcessingPipeline(config=pipe_config, data_path=data_path)
    result = pipeline.run(data_path=data_path, run_eda=False, run_feature_selection=True)

    X_train = result.X_train.values
    X_val = result.X_val.values if len(result.X_val) > 0 else None
    X_test = result.X_test.values
    y_train = result.y_train.values
    y_val = result.y_val.values if len(result.y_val) > 0 else None
    y_test = result.y_test.values
    labels = list(result.y_test.unique())

    from clinical_ml_pipeline.calibration import _get_calibration_data, wrap_with_calibration
    from clinical_ml_pipeline.full_pipeline import (
        _get_sample_weights,
        _LabelEncoderWrapper,
        _retrain_best_on_full,
    )
    from clinical_ml_pipeline.models import create_model
    from clinical_ml_pipeline.threshold_optimizer import (
        ThresholdOptimizedClassifier,
        optimize_thresholds_cost_sensitive,
    )
    from sklearn.preprocessing import LabelEncoder

    X_cal, y_cal = _get_calibration_data(
        X_train, y_train, X_val, y_val, cal_ratio=0.2, random_state=42
    )
    sample_weight = _get_sample_weights(imb, y_train, labels)

    logger.info("Training %s (%s, %s)...", model_name, imb, cal_method)
    est = create_model(model_name, **params)
    fit_kw = {}
    if sample_weight is not None:
        fit_kw["sample_weight"] = sample_weight
    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train.astype(str))
    est.fit(X_train, y_train_enc, **fit_kw)
    est = _LabelEncoderWrapper(est, le)

    if cal_method != "none" and hasattr(est, "predict_proba"):
        est = wrap_with_calibration(est, X_cal, y_cal, method=cal_method)

    apply_thresh = best.get("threshold_optimized", False)
    if apply_thresh and hasattr(est, "predict_proba"):
        thresh, _, _ = optimize_thresholds_cost_sensitive(
            est, X_val if X_val is not None else X_cal,
            y_val if y_val is not None else y_cal, labels,
        )
        est = ThresholdOptimizedClassifier(est, thresh, labels)

    best_metrics = {
        "model": model_name,
        "imbalance": imb,
        "calibration_method": cal_method,
        "best_params": params,
        "accuracy": float(best.get("accuracy", 0)),
        "f1_weighted": float(best.get("f1_weighted", 0)),
        "f1_macro": float(best.get("f1_macro", 0)),
        "roc_auc": float(best.get("roc_auc", 0)),
        "clinical_cost": float(best.get("clinical_cost", 0)),
        "overfitting_gap": float(best.get("overfitting_gap", 0)),
    }

    trained_models = {f"{model_name}_{imb}_{cal_method}": (est, params)}
    best_estimator, best_metrics = _retrain_best_on_full(
        est, best_metrics, X_train, y_train, X_val, y_val, labels,
        trained_models, apply_thresh, 42,
    )

    bundle = InferenceBundle(
        result,
        best_estimator,
        best_metrics.get("model", "best"),
        metric_name="f1_weighted",
        metric_value=best_metrics.get("f1_weighted", 0),
        calibration_method=best_metrics.get("calibration_method", "none"),
        threshold_optimized=apply_thresh,
    )
    save_best_model(bundle, best_model_dir)

    report = {
        "best_model": best_metrics.get("model"),
        "metrics": best_metrics,
        "selection": "multi_objective_from_experiment_table",
        "improvements": {
            "multi_objective_selection": True,
            "probability_calibration": cal_method != "none",
            "calibration_method": cal_method,
        },
    }
    report_path = output_dir / "final_evaluation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info("Deployed: %s (%s) F1=%.4f cost=%.4f",
                best_metrics.get("model"), cal_method,
                best_metrics.get("f1_weighted"), best_metrics.get("clinical_cost"))
    logger.info("Bundle: %s", best_model_dir / "inference_bundle.joblib")
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--table", type=Path, default=REPO_ROOT / "outputs/clinical_ml_experiments/experiment_table.csv")
    p.add_argument("--data", type=Path, default=REPO_ROOT / "data" / "SmartSensor_DiabetesMonitoring.csv")
    p.add_argument("--best-model-dir", type=Path, default=REPO_ROOT / "outputs/best_model")
    p.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/clinical_ml_experiments")
    p.add_argument("--patient-split", action="store_true", help="Use patient-based split when retraining")
    args = p.parse_args()
    sys.exit(main(
        table_path=args.table,
        data_path=args.data,
        best_model_dir=args.best_model_dir,
        output_dir=args.out_dir,
        use_patient_split=args.patient_split,
    ))
