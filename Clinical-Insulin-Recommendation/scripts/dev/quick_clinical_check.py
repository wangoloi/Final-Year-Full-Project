"""Fast one-model smoke test for clinical_insulin_pipeline (RandomForest baseline)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "backend" / "src"))

from clinical_insulin_pipeline.data import prepare_dataset
from clinical_insulin_pipeline.preprocessing import build_preprocessor, fit_transform_preprocessor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error


def main() -> int:
    p = _ROOT / "data" / "SmartSensor_DiabetesMonitoring.csv"
    print("loading csv...", flush=True)
    ds = prepare_dataset(p)
    print("train", len(ds.X_train), "test", len(ds.X_test), flush=True)
    pre = build_preprocessor()
    Xtr, Xte, _ = fit_transform_preprocessor(pre, ds.X_train, ds.X_test)
    print("fitting rf...", flush=True)
    m = RandomForestRegressor(n_estimators=50, n_jobs=1, random_state=42)
    m.fit(Xtr, ds.y_train.values)
    pred = m.predict(Xte)
    rmse = float(np.sqrt(mean_squared_error(ds.y_test.values, pred)))
    print("rmse", rmse, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
