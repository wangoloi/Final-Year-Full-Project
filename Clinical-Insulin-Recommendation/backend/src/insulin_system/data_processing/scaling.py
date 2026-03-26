"""
Feature scaling module.

Scales continuous features (e.g. StandardScaler, MinMaxScaler) for model compatibility.
Fitted on training data only; same scaling applied to val/test.
"""

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from ..config.schema import DataSchema
from ..exceptions import DataValidationError

logger = logging.getLogger(__name__)


class FeatureScaler:
    """
    Scales numeric features. Supports standard, minmax, or robust.
    Excludes ID and target; only scales schema numeric columns.
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        scaler_type: str = "standard",
        extra_numeric_columns: Optional[List[str]] = None,
    ) -> None:
        self._schema = schema or DataSchema()
        if scaler_type not in ("standard", "minmax", "robust"):
            raise DataValidationError(
                "scaler_type must be one of standard, minmax, robust; got " + scaler_type
            )
        self._scaler_type = scaler_type
        self._extra_numeric = list(extra_numeric_columns or [])
        self._scaler = None
        self._numeric_columns: List[str] = []

    def _make_scaler(self):
        if self._scaler_type == "standard":
            return StandardScaler()
        if self._scaler_type == "minmax":
            return MinMaxScaler()
        try:
            from sklearn.preprocessing import RobustScaler
            return RobustScaler()
        except ImportError:
            return StandardScaler()

    def fit(self, df: pd.DataFrame) -> "FeatureScaler":
        """Fit scaler on numeric feature columns present in df."""
        base = [c for c in self._schema.NUMERIC if c in df.columns]
        extra = [c for c in self._extra_numeric if c in df.columns]
        self._numeric_columns = base + extra
        if not self._numeric_columns:
            return self
        self._scaler = self._make_scaler()
        self._scaler.fit(df[self._numeric_columns])
        logger.info("FeatureScaler fitted (%s) on %s", self._scaler_type, self._numeric_columns)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scale numeric columns; leave others unchanged."""
        out = df.copy()
        if self._scaler is None or not self._numeric_columns:
            return out
        cols_present = [c for c in self._numeric_columns if c in out.columns]
        if not cols_present:
            return out
        out[cols_present] = self._scaler.transform(out[cols_present])
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    @property
    def is_fitted(self) -> bool:
        return self._scaler is not None
