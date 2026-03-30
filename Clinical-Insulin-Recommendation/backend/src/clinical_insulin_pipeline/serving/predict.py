"""Load joblib bundle and predict insulin dose with safety post-processing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd

from ..data.features import (
    add_cyclical_time_features,
    add_derived_clinical_features,
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
    df = add_cyclical_time_features(df, "Timestamp")
    df = add_derived_clinical_features(df)
    cols = feature_columns_after_engineering()
    for c in cols:
        if c not in df.columns:
            raise ValueError(f"Missing feature column: {c}")
    X = df[cols].astype(float)
    pre = bundle["preprocessor"]
    model = bundle["model"]
    Xt = pre.transform(X)
    raw = float(model.predict(Xt)[0])
    return postprocess_dose(raw)


def predict_from_insulin_prediction_input(
    bundle: Dict[str, Any], inp: InsulinPredictionInput
) -> float:
    return predict_insulin_dose(bundle, row_dict_from_input(inp))
