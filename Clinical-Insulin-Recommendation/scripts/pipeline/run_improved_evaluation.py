"""
Run improved ML evaluation pipeline with enhanced features, stacking ensemble,
and better hyperparameter tuning.

Usage: python scripts/pipeline/run_improved_evaluation.py [--data PATH] [--no-stacking] [--no-eda]
"""

import argparse
import logging
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*class_weight.*", category=UserWarning)

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))
from insulin_system.config.schema import PipelineConfig, ModelConfig
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.models import ModelTrainer, EvaluationFramework
from insulin_system.persistence import InferenceBundle, save_best_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Improved ML evaluation: enhanced features, stacking, better tuning"
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV)
    parser.add_argument("--no-eda", action="store_true")
    parser.add_argument("--models", nargs="*", help="Model names (default: all including stacking)")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/evaluation")
    parser.add_argument("--best-model-dir", type=Path, default=REPO_ROOT / "outputs/best_model")
    parser.add_argument("--no-feature-selection", action="store_true")
    parser.add_argument("--random-split", action="store_true")
    parser.add_argument("--no-stacking", action="store_true", help="Exclude stacking ensemble")
    parser.add_argument("--n-jobs", type=int, default=None)
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Running data pipeline (enhanced features: glucose_zone, iob*carbs)...")
    pipe_config = PipelineConfig(split_type="random") if args.random_split else None
    pipeline = DataProcessingPipeline(config=pipe_config, data_path=args.data)
    pipeline_result = pipeline.run(
        data_path=args.data,
        run_eda=not args.no_eda,
        run_feature_selection=not args.no_feature_selection,
    )
    logger.info(
        "Train=%s Val=%s Test=%s Features=%s",
        len(pipeline_result.X_train),
        len(pipeline_result.X_val),
        len(pipeline_result.X_test),
        len(pipeline_result.feature_names),
    )

    model_config = ModelConfig(n_jobs=args.n_jobs) if args.n_jobs is not None else None
    trainer = ModelTrainer(
        config=model_config,
        exclude_mlp=True,
        include_rnn=False,
        include_stacking=not args.no_stacking,
    )
    logger.info("Training models (including stacking ensemble)...")
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
    logger.info(
        "Best model saved: %s (f1_weighted=%.4f) -> %s",
        best_model_name,
        best_f1,
        args.best_model_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
