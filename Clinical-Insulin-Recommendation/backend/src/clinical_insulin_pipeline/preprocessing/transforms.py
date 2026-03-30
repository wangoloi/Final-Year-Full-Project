"""KNN imputation + Robust scaling (fit on train only)."""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from ..config import KNN_NEIGHBORS_IMPUTER


def build_preprocessor() -> Pipeline:
    return Pipeline(
        [
            ("imputer", KNNImputer(n_neighbors=KNN_NEIGHBORS_IMPUTER)),
            ("scaler", RobustScaler()),
        ]
    )


def fit_transform_preprocessor(
    pipe: Pipeline, X_train: pd.DataFrame, X_test: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    names = list(X_train.columns)
    Xt = pipe.fit_transform(X_train)
    Xv = pipe.transform(X_test)
    return Xt, Xv, names
