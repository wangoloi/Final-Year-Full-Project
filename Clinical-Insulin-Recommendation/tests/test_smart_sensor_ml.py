"""Smoke tests for Smart Sensor ML pipeline (regression)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from smart_sensor_ml import config
from smart_sensor_ml.load_data import load_data, enrich_training_dataframe
from smart_sensor_ml.preprocess import PreprocessPipeline, insulin_dose_to_tier_name
from smart_sensor_ml.train_model import train_regression_model
from smart_sensor_ml.validate_data import validate_data


def test_smart_sensor_csv_load_and_preprocess():
    p = Path(__file__).resolve().parent.parent / "data" / "SmartSensor_DiabetesMonitoring.csv"
    if not p.exists():
        pytest.skip("SmartSensor CSV not found")
    df = enrich_training_dataframe(load_data(p))
    df, _ = validate_data(df)
    g = df[config.COL_PATIENT].astype(str)
    train_df = df[g.isin(g.unique()[:80])].reset_index(drop=True)
    test_df = df[~g.isin(g.unique()[:80])].reset_index(drop=True)
    if len(train_df) < 100 or len(test_df) < 20:
        pytest.skip("Not enough rows for split smoke test")

    pre = PreprocessPipeline()
    pre.fit(train_df)
    pre.select_top_n(len(pre.mi_ranked_final), train_df)
    X_tr = pre.transform(train_df)
    X_te = pre.transform(test_df)
    y_tr = pd.to_numeric(train_df[config.COL_TARGET], errors="coerce").values.astype(float)
    y_te = pd.to_numeric(test_df[config.COL_TARGET], errors="coerce").values.astype(float)

    model = train_regression_model("ridge", X_tr, y_tr, random_state=42)
    pred = model.predict(X_te)
    assert len(pred) == len(y_te)
    assert np.isfinite(pred).all()
    d0 = float(pred[0])
    _, tier = insulin_dose_to_tier_name(d0, pre.insulin_bin_edges)
    assert tier in config.CLASS_NAMES
