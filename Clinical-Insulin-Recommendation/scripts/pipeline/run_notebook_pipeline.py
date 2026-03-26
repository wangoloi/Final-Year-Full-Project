"""
Run the ML pipeline based on the notebook (insulin_prediction_development.ipynb).

Uses: LabelEncoder for categoricals, mutual_info for feature selection,
      StandardScaler, 80/10/10 stratified split, same models as notebook.
Saves to outputs/best_model for use by the API.

Usage: python scripts/pipeline/run_notebook_pipeline.py [--data PATH] [--out-dir DIR] [--model NAME]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore", message=".*class_weight.*", category=UserWarning)

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))
from insulin_system.data_processing.notebook_pipeline import run_notebook_pipeline
from insulin_system.persistence import NotebookInferenceBundle, save_best_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODELS = {
    "logistic_regression": LogisticRegression(max_iter=2000, random_state=42, class_weight="balanced"),
    "decision_tree": DecisionTreeClassifier(random_state=42, class_weight="balanced"),
    "random_forest": RandomForestClassifier(random_state=42, class_weight="balanced"),
    "gradient_boosting": GradientBoostingClassifier(random_state=42),
}


def main():
    parser = argparse.ArgumentParser(description="Run notebook-based ML pipeline")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/best_model")
    parser.add_argument("--model", type=str, default=None, help="Train only this model (default: all)")
    parser.add_argument("--top-k", type=int, default=15, help="Top K features from mutual info")
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        return 1

    logger.info("Running notebook-based pipeline...")
    result = run_notebook_pipeline(args.data, top_k=args.top_k)

    model_names = [args.model] if args.model else list(MODELS.keys())
    model_names = [m for m in model_names if m in MODELS]
    if not model_names:
        logger.error("No valid models: %s", args.model)
        return 1

    logger.info("Training models: %s", model_names)
    scores = {}
    fitted = {}

    for name in model_names:
        model = MODELS[name]
        logger.info("Training %s...", name)
        start = time.time()
        model.fit(result.X_train, result.y_train)
        elapsed = time.time() - start
        fitted[name] = model
        y_pred = model.predict(result.X_test)
        f1 = f1_score(result.y_test, y_pred, average="weighted")
        scores[name] = f1
        logger.info("  %s: f1_weighted=%.4f (%.2fs)", name, f1, elapsed)

    best_name = max(scores, key=scores.get)
    best_f1 = scores[best_name]
    best_estimator = fitted[best_name]

    bundle = NotebookInferenceBundle(
        model=best_estimator,
        scaler=result.scaler,
        label_encoders=result.label_encoders,
        feature_names=result.feature_names,
        model_name=best_name,
        metric_name="f1_weighted",
        metric_value=best_f1,
    )
    save_best_model(bundle, args.out_dir)

    logger.info("Best model: %s (f1_weighted=%.4f) -> %s", best_name, best_f1, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
