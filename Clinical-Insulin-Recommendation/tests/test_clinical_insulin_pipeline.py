"""Smoke tests for clinical insulin regression pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend" / "src"))

from clinical_insulin_pipeline.data import prepare_dataset
from clinical_insulin_pipeline.metrics import regression_metrics
from clinical_insulin_pipeline.schema import InsulinPredictionInput, postprocess_dose


def test_postprocess_dose_clamps_and_rounds():
    assert postprocess_dose(-1.0) == 0.0
    assert postprocess_dose(12.0) == 10.0
    assert postprocess_dose(3.24) == 3.0
    assert postprocess_dose(3.26) == 3.5


def test_regression_metrics_basic():
    y = np.array([1.0, 2.0, 3.0])
    p = np.array([1.1, 2.0, 2.5])
    m = regression_metrics(y, p)
    assert "rmse" in m and "mae" in m and m["rmse"] >= 0


@pytest.mark.slow
def test_prepare_dataset_smoke():
    csv_path = _ROOT / "data" / "SmartSensor_DiabetesMonitoring.csv"
    if not csv_path.is_file():
        pytest.skip("Dataset CSV not present")
    ds = prepare_dataset(csv_path)
    assert len(ds.X_train) > 0 and len(ds.X_test) > 0
    assert ds.X_train.shape[1] == len(ds.feature_names)


def test_insulin_prediction_input_dict():
    inp = InsulinPredictionInput(bmi=26.0, hba1c=6.0)
    d = inp.to_feature_row_dict()
    assert "Timestamp" in d and "BMI" in d
