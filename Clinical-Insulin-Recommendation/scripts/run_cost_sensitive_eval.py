#!/usr/bin/env python3
"""
Run evaluation with cost-sensitive learning (2x weight for down/no).
Outputs to outputs/evaluation_costsensitive. Compares to baseline.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from insulin_system.config.schema import ModelConfig, PipelineConfig
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.models import ModelTrainer, EvaluationFramework
from insulin_system.persistence import InferenceBundle, save_best_model


def main():
    out_dir = REPO_ROOT / "outputs/evaluation_costsensitive"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Cost-sensitive config: 2x weight for minority classes (down, no)
    model_config = ModelConfig(
        imbalance_strategy="class_weight",
        minority_class_weight_multiplier=2.0,
        minority_classes=("down", "no"),
        use_calibration=False,
        random_search_n_iter=15,  # Faster for quick eval
    )

    data_path = REPO_ROOT / "data" / "SmartSensor_DiabetesMonitoring.csv"
    if not data_path.exists():
        print(f"Error: {data_path} not found")
        return 1

    print("Running pipeline with cost-sensitive learning (2x for down/no)...")
    pipeline = DataProcessingPipeline(config=PipelineConfig(), data_path=data_path)
    result = pipeline.run(data_path=data_path, run_eda=False, run_feature_selection=True)

    trainer = ModelTrainer(config=model_config, exclude_mlp=False, include_rnn=True)
    training_results = trainer.train_all(
        result.X_train, result.y_train,
        model_names=["logistic_regression", "random_forest", "gradient_boosting"],
    )

    if not training_results:
        print("No models trained")
        return 1

    models = [(r.model_name, r.best_estimator) for r in training_results]
    framework = EvaluationFramework()
    summary_df = framework.run_for_many(models, result, output_dir=out_dir)

    print("\nCost-sensitive evaluation summary:")
    print(summary_df.to_string())

    best_row = summary_df.iloc[0]
    best_estimator = next(est for name, est in models if name == str(best_row["model"]))
    bundle = InferenceBundle(
        result, best_estimator, str(best_row["model"]),
        metric_name="f1_weighted", metric_value=float(best_row["f1_weighted"]),
    )
    save_best_model(bundle, Path("outputs/best_model"))
    print(f"\nBest model saved: {best_row['model']} (f1_weighted={best_row['f1_weighted']:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
