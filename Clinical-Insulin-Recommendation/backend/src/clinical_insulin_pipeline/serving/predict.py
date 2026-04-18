"""Load joblib bundle and predict insulin dose with safety post-processing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd

from ..data.features import (
    add_cyclical_time_features,
    add_derived_clinical_features,
    add_time_series_features,
    feature_columns_after_engineering,
)
from .schema import InsulinPredictionInput, postprocess_dose


def load_bundle(path: Union[str, Path]) -> Any:
    import joblib

    return joblib.load(path)


def row_dict_from_input(inp: InsulinPredictionInput) -> Dict[str, Any]:
    return inp.to_feature_row_dict()


def predict_insulin_dose(bundle: Dict[str, Any], row: Dict[str, Any]) -> float:
    """
    `row` must include Timestamp and all raw sensor/clinical columns used in training
    (see InsulinPredictionInput / feature engineering).
    """
    df = pd.DataFrame([row])
    df = add_derived_clinical_features(df)
    # Training builds time series features grouped by Patient_ID. For single-row inference,
    # we synthesize a stable patient id so shifts/rolling windows reduce to safe defaults.
    if "Patient_ID" not in df.columns:
        df["Patient_ID"] = "inference_patient"
    df = add_time_series_features(df, ts_col="Timestamp", patient_col="Patient_ID")
    df = add_cyclical_time_features(df, "Timestamp")

    cols = list(
        bundle.get("raw_feature_names")
        or bundle.get("feature_names")
        or feature_columns_after_engineering()
    )
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing feature column(s) for inference: {missing_cols}")

    X = df[cols].copy()
    # Coerce numerics but preserve categoricals (e.g. time_of_day_category).
    for c in X.columns:
        if c == "time_of_day_category":
            X[c] = X[c].astype(str)
        else:
            X[c] = pd.to_numeric(X[c], errors="coerce")
    pre = bundle["preprocessor"]
    model = bundle["model"]
    Xt = pre.transform(X)
    raw = float(model.predict(Xt)[0])
    return postprocess_dose(raw)


def predict_from_insulin_prediction_input(
    bundle: Dict[str, Any], inp: InsulinPredictionInput
) -> float:
    return predict_insulin_dose(bundle, row_dict_from_input(inp))
