"""
Missing value imputation module.

Strategies: median for numeric, mode for categorical (configurable).
Fitted state is stored so the same imputers can be applied to train and test.
"""

import logging
from typing import Any, Optional

import pandas as pd

from ..config.schema import DataSchema
from ..exceptions import DataValidationError

logger = logging.getLogger(__name__)


class MissingValueImputer:
    """
    Handles missing values with strategy-based imputation.
    Fits on training data and stores fill values for transform.
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        numeric_strategy: str = "median",
        categorical_strategy: str = "mode",
    ) -> None:
        self._schema = schema or DataSchema()
        self._numeric_strategy = numeric_strategy
        self._categorical_strategy = categorical_strategy
        self._numeric_fill = {}
        self._categorical_fill = {}
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "MissingValueImputer":
        """Compute fill values from the given DataFrame."""
        self._validate_columns(df)
        numeric_cols = list(self._schema.NUMERIC) + list(getattr(self._schema, "CONTEXTUAL_IMPUTE", ()))
        for col in numeric_cols:
            if col not in df.columns:
                continue
            if df[col].isnull().any():
                if self._numeric_strategy == "median":
                    self._numeric_fill[col] = df[col].median()
                elif self._numeric_strategy == "mean":
                    self._numeric_fill[col] = df[col].mean()
                else:
                    self._numeric_fill[col] = df[col].median()
                logger.debug("Imputer fit numeric %s -> %s", col, self._numeric_fill[col])
        for col in self._schema.CATEGORICAL:
            if col not in df.columns:
                continue
            if df[col].isnull().any():
                mode_vals = df[col].mode()
                self._categorical_fill[col] = mode_vals.iloc[0] if len(mode_vals) else ""
                logger.debug("Imputer fit categorical %s -> %s", col, self._categorical_fill[col])
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply stored fill values to missing entries. Does not mutate input."""
        if not self._fitted:
            raise DataValidationError("Imputer must be fitted before transform.")
        out = df.copy()
        for col, val in self._numeric_fill.items():
            if col in out.columns and out[col].isnull().any():
                out[col] = out[col].fillna(val)
        for col, val in self._categorical_fill.items():
            if col in out.columns and out[col].isnull().any():
                out[col] = out[col].fillna(val)
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit on df and return transformed copy."""
        return self.fit(df).transform(df)

    def _validate_columns(self, df: pd.DataFrame) -> None:
        required = list(self._schema.NUMERIC) + list(self._schema.CATEGORICAL)
        contextual = getattr(self._schema, "CONTEXTUAL_IMPUTE", ())
        for col in required + list(contextual):
            if col not in df.columns:
                raise DataValidationError(f"Expected column '{col}' not in DataFrame.")

    @property
    def is_fitted(self) -> bool:
        return self._fitted
