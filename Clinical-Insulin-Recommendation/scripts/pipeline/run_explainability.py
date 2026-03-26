"""
Run SHAP explainability (Step 5): global + local explanations and clinical reports.

Usage: python scripts/pipeline/run_explainability.py [--data PATH] [--model NAME] [--out-dir DIR] [--no-eda]
"""
import argparse
import logging
import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore", message=".*class_weight.*are not used", category=UserWarning)

from repo_paths import REPO_ROOT, SRC, DEFAULT_DATA_CSV

sys.path.insert(0, str(SRC))
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.models import ModelTrainer
from insulin_system.explainability import SHAPExplainer, ClinicalReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="SHAP explainability and clinical reports")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_CSV)
    parser.add_argument("--model", type=str, default="random_forest")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "outputs/explainability")
    parser.add_argument("--no-eda", action="store_true")
    parser.add_argument("--no-feature-selection", action="store_true")
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Running pipeline...")
    pipeline = DataProcessingPipeline(data_path=args.data)
    pipeline_result = pipeline.run(
        data_path=args.data,
        run_eda=not args.no_eda,
        run_feature_selection=not args.no_feature_selection,
    )

    logger.info("Training model: %s", args.model)
    trainer = ModelTrainer()
    training_results = trainer.train_all(
        pipeline_result.X_train,
        pipeline_result.y_train,
        model_names=[args.model],
    )
    if not training_results:
        logger.error("Model training failed")
        return 1
    estimator = training_results[0].best_estimator
    classes = getattr(estimator, "classes_", None) or list(pipeline_result.y_test.unique())

    X_train = pipeline_result.X_train.values
    X_test = pipeline_result.X_test.values
    y_test = pipeline_result.y_test.values
    feature_names = pipeline_result.feature_names

    logger.info("Fitting SHAP explainer...")
    explainer = SHAPExplainer()
    explainer.fit(estimator, X_train, feature_names)

    segment_col = None
    if "temporal_segment" in pipeline_result.test.columns:
        segment_col = pipeline_result.test["temporal_segment"].values
    result = explainer.explain(
        X_test,
        model_name=args.model,
        output_dir=args.out_dir,
        segment_col=segment_col,
    )
    logger.info("SHAP artifacts: %s", list(result.paths.keys()))

    logger.info("Generating clinical reports for sample patients...")
    clinical = ClinicalReportGenerator()
    proba = estimator.predict_proba(X_test) if hasattr(estimator, "predict_proba") else None
    y_pred = estimator.predict(X_test)
    n_reports = min(5, len(X_test))
    reports_dir = args.out_dir / args.model / "clinical_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(n_reports):
        sv_one = explainer.get_local_shap_values(X_test, sample_idx=idx)
        cf = explainer.counterfactual(
            X_test[idx],
            sv_one,
            y_pred[idx],
            np.array(classes),
            feature_names,
        )
        report = clinical.generate_patient_report(
            idx,
            X_test,
            y_pred[idx],
            proba[idx] if proba is not None else None,
            sv_one,
            feature_names,
            np.array(classes),
            y_true=y_test,
            counterfactuals=cf,
        )
        clinical.write_report_to_file(report, reports_dir / f"patient_{idx}.md")
        similar_indices = [s["index"] for s in report.similar_patients]
        if similar_indices:
            clinical.plot_similar_patients_comparison(
                X_test,
                idx,
                similar_indices,
                feature_names,
                top_k_features=8,
                save_path=reports_dir / f"patient_{idx}_similar_comparison.png",
            )
    logger.info("Reports saved to %s", reports_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
