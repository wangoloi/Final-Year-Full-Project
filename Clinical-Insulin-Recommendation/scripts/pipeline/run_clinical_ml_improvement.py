"""
Run full Clinical ML Improvement Pipeline (Phases 1-11).

Improves insulin adjustment prediction through:
- Pipeline audit (no SMOTE; class_weight and cost_sensitive only)
- Feature improvement (correlation removal in pipeline)
- Probability calibration (Platt/sigmoid and isotonic) before threshold optimization
- Class imbalance: class_weight, cost_sensitive (SMOTE removed per experiments)
- Models: XGBoost, LightGBM, CatBoost, RF, Extra Trees, Balanced RF, MLP
- Threshold optimization (cost-sensitive, after calibration)
- Stacking and soft-voting ensemble with calibrated base models
- Experiment tracking (model, calibration_method, threshold_optimized)
- Model selection (clinical_cost, F1, overfitting_gap)
- Retrain best on full data; save inference_bundle.joblib
- Evaluation report and model_comparison.csv

Usage:
  python scripts/pipeline/run_clinical_ml_improvement.py [--data PATH] [--out-dir DIR] [--max-experiments N]
"""

import argparse
import logging
import sys
from pathlib import Path

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))
from clinical_ml_pipeline.full_pipeline import run_full_improvement

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Full Clinical ML Improvement Pipeline")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/clinical_ml_experiments")
    parser.add_argument("--best-model-dir", type=Path, default=REPO_ROOT / "outputs/best_model")
    parser.add_argument("--random-split", action="store_true",
                        help="Use random stratified split")
    parser.add_argument("--temporal-split", action="store_true",
                        help="Use temporal split by patient_id")
    parser.add_argument("--patient-split", action="store_true",
                        help="Use patient-based split (no leakage; each patient in one split)")
    parser.add_argument("--max-experiments", type=int, default=None,
                        help="Limit number of model experiments (default: all)")
    parser.add_argument("--models", nargs="*",
                        default=["gradient_boosting", "random_forest", "extra_trees", "balanced_rf", "lightgbm", "catboost", "mlp"],
                        help="Models to train (SMOTE removed per experiments)")
    parser.add_argument("--imbalance", nargs="*",
                        default=["class_weight", "cost_sensitive"],
                        help="Imbalance strategies: class_weight, cost_sensitive (SMOTE removed)")
    parser.add_argument("--no-threshold-opt", action="store_true", help="Disable threshold optimization")
    parser.add_argument("--no-stacking", action="store_true", help="Disable stacking ensemble")
    args = parser.parse_args()

    use_patient = args.patient_split
    use_temporal = args.temporal_split
    use_random = not use_patient and not use_temporal
    result = run_full_improvement(
        data_path=args.data,
        output_dir=args.out_dir,
        best_model_dir=args.best_model_dir,
        use_random_split=use_random,
        use_patient_split=use_patient,
        models=args.models if args.models else None,
        imbalance_strategies=args.imbalance,
        max_experiments=args.max_experiments,
        apply_threshold_optimization=not args.no_threshold_opt,
        build_stacking=not args.no_stacking,
    )

    logger.info("Improvement complete. Best model: %s (calibration: %s)",
                result["metrics"].get("model"), result["metrics"].get("calibration_method", "none"))
    logger.info("F1-weighted: %.4f, Clinical cost: %.4f",
                result["metrics"].get("f1_weighted", 0),
                result["metrics"].get("clinical_cost", 0))
    logger.info("Inference bundle: %s", result["bundle_path"])
    logger.info("Report: %s", result["report_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
