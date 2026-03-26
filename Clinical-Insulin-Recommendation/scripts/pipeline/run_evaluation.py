"""
Run full Model Evaluation (Step 4): pipeline -> train models -> comprehensive evaluation.

Generates: metrics (train/val/test), confusion matrices, ROC-AUC OvR,
calibration curves, learning curves, feature importance, temporal validation.
Usage: python scripts/pipeline/run_evaluation.py [--data PATH] [--no-eda] [--models NAME1 NAME2] [--out-dir DIR]
"""
import argparse
import logging
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*class_weight.*are not used", category=UserWarning)

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))
from insulin_system.config.schema import PipelineConfig
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.models import ModelTrainer, EvaluationFramework
from insulin_system.persistence import InferenceBundle, save_best_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Full model evaluation (metrics, plots, importance, temporal)")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV)
    parser.add_argument("--no-eda", action="store_true")
    parser.add_argument("--models", nargs="*", help="Model names (default: all)")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/evaluation")
    parser.add_argument("--best-model-dir", type=Path, default=REPO_ROOT / "outputs/best_model",
                        help="Directory to save the best model for system inference")
    parser.add_argument("--no-feature-selection", action="store_true")
    parser.add_argument("--random-split", action="store_true",
                        help="Use random stratified train/test split (80/20) instead of temporal split")
    parser.add_argument("--include-mlp", action="store_true", help="Include MLP in model comparison")
    parser.add_argument("--n-jobs", type=int, default=None, help="Override n_jobs for training (use 1 on Windows if parallel crashes)")
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Running data pipeline...")
    pipe_config = None
    if args.random_split:
        pipe_config = PipelineConfig(split_type="random")
    pipeline = DataProcessingPipeline(config=pipe_config, data_path=args.data)
    pipeline_result = pipeline.run(
        data_path=args.data,
        run_eda=not args.no_eda,
        run_feature_selection=not args.no_feature_selection,
    )
    logger.info("Train=%s Val=%s Test=%s Features=%s",
                len(pipeline_result.X_train), len(pipeline_result.X_val), len(pipeline_result.X_test),
                len(pipeline_result.feature_names))

    from insulin_system.config.schema import ModelConfig
    model_config = ModelConfig(n_jobs=args.n_jobs) if args.n_jobs is not None else None
    logger.info("Training models (including RNN for full comparison; use --include-mlp for MLP)...")
    trainer = ModelTrainer(config=model_config, exclude_mlp=not args.include_mlp, include_rnn=True)
    training_results = trainer.train_all(
        pipeline_result.X_train,
        pipeline_result.y_train,
        model_names=args.models or None,
    )
    if not training_results:
        logger.error("No models trained successfully")
        return 1

    models = [(r.model_name, r.best_estimator) for r in training_results]
    logger.info("Running comprehensive evaluation...")
    framework = EvaluationFramework()
    summary_df = framework.run_for_many(models, pipeline_result, output_dir=args.out_dir)
    logger.info("Evaluation summary:\n%s", summary_df.to_string())

    # Save best model for system inference (by f1_weighted)
    best_row = summary_df.iloc[0]
    best_model_name = str(best_row["model"])
    best_f1 = float(best_row["f1_weighted"])
    best_estimator = next(est for name, est in models if name == best_model_name)
    bundle = InferenceBundle(
        pipeline_result,
        best_estimator,
        best_model_name,
        metric_name="f1_weighted",
        metric_value=best_f1,
    )
    save_best_model(bundle, args.best_model_dir)
    logger.info("Best model saved for insulin predictions: %s (f1_weighted=%.4f) -> %s", best_model_name, best_f1, args.best_model_dir)

    logger.info("Artifacts saved under %s", args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
