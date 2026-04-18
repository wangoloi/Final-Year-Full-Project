"""Preprocessing for numeric and categorical insulin regression features."""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler


def build_preprocessor() -> Pipeline:
    numeric_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value="Missing")),
            (
                "encoder",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("num", numeric_pipe, make_column_selector(dtype_include=np.number)),
            ("cat", categorical_pipe, ["time_of_day_category"]),
        ],
        remainder="drop",
    )
    return Pipeline([("preprocessor", preprocessor)])


def fit_transform_preprocessor(
    pipe: Pipeline, X_train: pd.DataFrame, X_test: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    Xt = pipe.fit_transform(X_train)
    Xv = pipe.transform(X_test)
    feature_names = []
    if hasattr(pipe.named_steps["preprocessor"], "get_feature_names_out"):
        feature_names = list(
            pipe.named_steps["preprocessor"].get_feature_names_out(X_train.columns)
        )
    else:
        feature_names = list(X_train.columns)
    return Xt, Xv, feature_names
