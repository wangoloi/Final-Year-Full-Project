"""
Run model development: data pipeline -> train all models (with tuning) -> evaluate and compare.
Usage: python scripts/pipeline/run_models.py [--data PATH] [--no-eda] [--models NAME1 NAME2] [--out-dir DIR]
"""
import argparse
import logging
import sys
import warnings
from pathlib import Path

# Suppress XGBoost "class_weight not used" warnings (we use sample_weight instead)
warnings.filterwarnings("ignore", message=".*class_weight.*are not used", category=UserWarning)

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.models import ModelTrainer, compare_models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Train and compare insulin dosage models")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV)
    parser.add_argument("--no-eda", action="store_true")
    parser.add_argument("--models", nargs="*", help="Model names to train (default: all)")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/models")
    parser.add_argument("--no-feature-selection", action="store_true")
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Running data pipeline...")
    pipeline = DataProcessingPipeline(data_path=args.data)
    result = pipeline.run(
        data_path=args.data,
        run_eda=not args.no_eda,
        run_feature_selection=not args.no_feature_selection,
    )
    X_train, y_train = result.X_train, result.y_train
    X_test, y_test = result.X_test, result.y_test
    logger.info("Train=%s Test=%s Features=%s", len(X_train), len(X_test), len(result.feature_names))

    logger.info("Training models (tuning + stratified CV)...")
    trainer = ModelTrainer()
    training_results = trainer.train_all(X_train, y_train, model_names=args.models or None)
    if not training_results:
        logger.error("No models trained successfully")
        return 1

    labels = list(y_test.unique())
    comparison = compare_models(training_results, X_test.values, y_test.values, labels=labels)
    comparison = comparison.sort_values("f1_weighted", ascending=False)
    logger.info("Model comparison (test):\n%s", comparison.to_string())
    comparison.to_csv(args.out_dir / "model_comparison.csv", index=False)
    logger.info("Saved to %s", args.out_dir / "model_comparison.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
