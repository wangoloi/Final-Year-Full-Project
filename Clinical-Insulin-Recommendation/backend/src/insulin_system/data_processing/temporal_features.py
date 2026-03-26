"""
Temporal feature creator (when applicable).

Adds position/rank or segment features when a temporal or ordering column exists
(e.g. patient_id as proxy for time). Optional; no-op if no order column configured.
"""

import logging
from typing import List, Optional

import pandas as pd

from ..config.schema import DataSchema, FeatureEngineeringConfig
from ..exceptions import DataValidationError

logger = logging.getLogger(__name__)


def _order_column_numeric(series: pd.Series) -> pd.Series:
    """Values for ordering/quantiles: numeric as-is; string IDs -> stable integer codes."""
    num = pd.to_numeric(series, errors="coerce")
    if num.notna().sum() >= max(1, len(series) // 2):
        return num.fillna(0.0).astype(float)
    codes, _ = pd.factorize(series, sort=True)
    return pd.Series(codes.astype(float), index=series.index)


class TemporalFeatureCreator:
    """
    Creates temporal/order-based features when an order column is configured.
    - temporal_rank: normalized rank (0-1) by order column (simulates time order).
    - temporal_segment: quartile segment (1-4) for train/val/test consistency.
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        config: Optional[FeatureEngineeringConfig] = None,
    ) -> None:
        self._schema = schema or DataSchema()
        self._config = config or FeatureEngineeringConfig()
        self._order_col: Optional[str] = None
        self._created_columns: List[str] = []
        self._quantiles: Optional[list] = None  # for segment boundaries from fit

    def fit(self, df: pd.DataFrame) -> "TemporalFeatureCreator":
        """Determine order column and compute segment quantiles if applicable."""
        self._created_columns = []
        self._order_col = None
        if not self._config.TEMPORAL_ORDER_COLUMN:
            return self
        col = self._config.TEMPORAL_ORDER_COLUMN
        if col not in df.columns:
            logger.debug("Temporal order column %s not in DataFrame; skipping temporal features", col)
            return self
        self._order_col = col
        order_vals = _order_column_numeric(df[col])
        self._quantiles = [
            order_vals.quantile(0.25),
            order_vals.quantile(0.5),
            order_vals.quantile(0.75),
        ]
        self._created_columns = ["temporal_rank", "temporal_segment"]
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add temporal_rank and temporal_segment. Does not mutate input. Coerces order column to numeric for comparison."""
        out = df.copy()
        if self._order_col is None:
            return out
        col = self._order_col
        if col not in out.columns:
            return out
        order_vals = _order_column_numeric(out[col])
        ranks = order_vals.rank(method="average", pct=True)
        out["temporal_rank"] = ranks.values
        q1, q2, q3 = self._quantiles
        if q1 is None or q2 is None or q3 is None:
            out["temporal_segment"] = 1
            return out
        try:
            q1, q2, q3 = float(q1), float(q2), float(q3)
        except (TypeError, ValueError):
            out["temporal_segment"] = 1
            return out
        seg = pd.Series(1, index=out.index)
        seg[order_vals > q1] = 2
        seg[order_vals > q2] = 3
        seg[order_vals > q3] = 4
        out["temporal_segment"] = seg.values
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    @property
    def temporal_columns(self) -> List[str]:
        return list(self._created_columns)
