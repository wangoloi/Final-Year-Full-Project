"""
Entry point to run the data processing pipeline.

Usage:
  python run_data_pipeline.py [--data PATH] [--no-eda] [--eda-dir PATH]

Example:
  python scripts/pipeline/run_data_pipeline.py --data data/SmartSensor_DiabetesMonitoring.csv
"""

import argparse
import logging
import sys
from pathlib import Path

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))

from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.exceptions import DataLoadError, DataValidationError, PipelineError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run insulin dosage data processing pipeline")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_CSV,
        help="Path to training CSV (default: data/SmartSensor_DiabetesMonitoring.csv)",
    )
    parser.add_argument(
        "--no-eda",
        action="store_true",
        help="Skip EDA and visualizations",
    )
    parser.add_argument(
        "--eda-dir",
        type=Path,
        default=REPO_ROOT / "outputs/eda",
        help="Directory for EDA outputs",
    )
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        return 1

    try:
        pipeline = DataProcessingPipeline(data_path=args.data)
        result = pipeline.run(
            data_path=args.data,
            run_eda=not args.no_eda,
            eda_output_dir=args.eda_dir,
        )
        logger.info(
            "Pipeline complete. Train=%s, Val=%s, Test=%s. Features=%s",
            len(result.X_train),
            len(result.X_val),
            len(result.X_test),
            len(result.feature_names),
        )
        return 0
    except (DataLoadError, DataValidationError, PipelineError) as e:
        logger.exception("Pipeline failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
