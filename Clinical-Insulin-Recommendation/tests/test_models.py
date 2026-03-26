"""Tests for Model Development module."""

import numpy as np
import pandas as pd
import pytest
from insulin_system.config.schema import ModelConfig
from insulin_system.models import (
    get_model_definitions,
    MODEL_NAMES,
    ModelTrainer,
    compare_models,
    evaluate_model,
)
from insulin_system.models.training import TrainingResult


def test_model_definitions_include_baseline_and_advanced():
    defs = get_model_definitions()
    assert "logistic_regression" in defs
    assert "decision_tree" in defs
    assert "random_forest" in defs
    assert "gradient_boosting" in defs
    assert "mlp" in defs
    for name in defs:
        est, grid = defs[name]
        # rnn_lstm uses custom training; est is None placeholder
        if name != "rnn_lstm":
            assert hasattr(est, "fit"), f"{name} should have fit method"
        assert isinstance(grid, dict)


def test_train_single_returns_training_result(sample_raw_df):
    import pandas as pd
    from insulin_system.data_processing.pipeline import DataProcessingPipeline
    from pathlib import Path
    data_path = Path(__file__).resolve().parent.parent / "data" / "SmartSensor_DiabetesMonitoring.csv"
    if not data_path.exists():
        pytest.skip("Dataset not found")
    if "Insulin" not in pd.read_csv(data_path, nrows=0).columns:
        pytest.skip("Legacy ModelTrainer test requires legacy CSV schema")
    pipeline = DataProcessingPipeline(data_path=data_path)
    result = pipeline.run(data_path=data_path, run_eda=False)
    config = ModelConfig(cv_folds=2, random_search_n_iter=2)
    trainer = ModelTrainer(config=config)
    res = trainer.train_single(
        "logistic_regression",
        result.X_train,
        result.y_train,
    )
    assert isinstance(res, TrainingResult)
    assert res.model_name == "logistic_regression"
    assert res.best_estimator is not None
    assert res.best_cv_score >= 0


def test_evaluate_model_returns_metrics():
    from sklearn.linear_model import LogisticRegression
    X = np.random.randn(50, 5)
    y = np.array(["a"] * 20 + ["b"] * 20 + ["c"] * 10)
    clf = LogisticRegression().fit(X, y)
    ev = evaluate_model(clf, X, y, model_name="lr", labels=["a", "b", "c"])
    assert 0 <= ev.accuracy <= 1
    assert ev.confusion_matrix.shape == (3, 3)
