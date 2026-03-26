"""Tests for the full data processing pipeline."""

import pandas as pd
import pytest

from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.exceptions import PipelineError


def test_pipeline_run_requires_path():
    pipeline = DataProcessingPipeline()
    with pytest.raises(PipelineError):
        pipeline.run()


def test_pipeline_run_success(data_path):
    if not data_path.exists():
        pytest.skip("Dataset not found")
    if "Insulin" not in pd.read_csv(data_path, nrows=0).columns:
        pytest.skip("Legacy pipeline expects legacy CSV (e.g. Insulin column); default data is SmartSensor format")
    pipeline = DataProcessingPipeline(data_path=data_path)
    result = pipeline.run(data_path=data_path, run_eda=False)
    assert result.X_train.shape[0] > 0
    assert result.X_val.shape[0] > 0
    assert result.X_test.shape[0] > 0
    assert len(result.feature_names) > 0
    assert result.y_train.name == "Insulin"
    assert result.imputer is not None
    assert result.encoder is not None
    assert result.scaler is not None
