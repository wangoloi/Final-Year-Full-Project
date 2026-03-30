"""CLI: train pipeline and write outputs/clinical_insulin_pipeline/latest/."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ..config import DEFAULT_DATA_CSV, OUTPUT_SUBDIR, repo_root_from_here
from .runner import run_training

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Clinical insulin dose regression pipeline (0-10 IU)")
    p.add_argument(
        "--data",
        type=Path,
        default=None,
        help=f"CSV path (default: repo/{DEFAULT_DATA_CSV})",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"Output directory (default: repo/{OUTPUT_SUBDIR}/latest)",
    )
    p.add_argument("--skip-learning-curve", action="store_true", help="Faster run")
    p.add_argument("--skip-shap", action="store_true", help="Skip SHAP plot")
    args = p.parse_args(argv)

    root = repo_root_from_here()
    data = args.data or (root / DEFAULT_DATA_CSV)
    if not data.is_file():
        logger.error("Data file not found: %s", data)
        return 1

    out = args.out
    if out is None:
        out = root / OUTPUT_SUBDIR / "latest"

    res = run_training(
        data.resolve(),
        out_dir=out.resolve(),
        skip_learning_curve=args.skip_learning_curve,
        skip_shap=args.skip_shap,
    )
    logger.info("Best model: %s RMSE=%.4f", res.best_name, res.test_metrics["rmse"])
    logger.info("Bundle: %s", res.output_dir / "insulin_regression_bundle.joblib")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
