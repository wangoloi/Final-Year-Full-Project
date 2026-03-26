"""
Outlier detection and handling with clinical validation.

Uses configurable clinical bounds to identify out-of-range values and
apply strategy: clip to bounds, remove rows, or only flag.
"""

import logging
from typing import Optional, Tuple

import pandas as pd

from ..config.schema import ClinicalBounds, DataSchema
from ..exceptions import DataValidationError

logger = logging.getLogger(__name__)


class OutlierHandler:
    """
    Applies clinical bounds to numeric columns and handles violations.

    Strategy: "clip" (cap to min/max), "remove" (drop rows with any out-of-bound),
    or "flag" (add a column indicating violation, then clip for modeling).
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        bounds: Optional[ClinicalBounds] = None,
        strategy: str = "clip",
    ) -> None:
        self._schema = schema or DataSchema()
        self._bounds = bounds or ClinicalBounds()
        if strategy not in ("clip", "remove", "flag"):
            raise DataValidationError(
                f"outlier strategy must be one of clip, remove, flag; got {strategy}"
            )
        self._strategy = strategy
        self._n_clipped: Optional[int] = 0
        self._n_removed: Optional[int] = 0

    def fit(self, df: pd.DataFrame) -> "OutlierHandler":
        """
        No learned state; validates that numeric columns exist.
        Exists for API consistency with pipeline.
        """
        numeric_cols = list(self._schema.NUMERIC) + list(getattr(self._schema, "CONTEXTUAL_IMPUTE", ()))
        for col in numeric_cols:
            if col not in df.columns:
                raise DataValidationError(f"Expected numeric column '{col}' not in DataFrame.")
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply outlier handling: clip and/or remove rows.

        Returns:
            New DataFrame; input is not mutated.
        """
        out = df.copy()
        n_clipped = 0
        numeric_cols = list(self._schema.NUMERIC) + list(getattr(self._schema, "CONTEXTUAL_IMPUTE", ()))
        for col in numeric_cols:
            if col not in out.columns:
                continue
            # Ensure numeric type to avoid "Invalid comparison between dtype=str and float64"
            try:
                out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)
            except Exception:
                continue
            try:
                low, high = self._bounds.get_bounds_for_column(col)
            except KeyError:
                continue
            if low is None or high is None:
                continue
            below = (out[col] < low).sum()
            above = (out[col] > high).sum()
            if below > 0 or above > 0:
                n_clipped += int(((out[col] < low) | (out[col] > high)).sum())
                out[col] = out[col].clip(lower=low, upper=high)
                logger.debug("OutlierHandler clipped %s: below=%s, above=%s", col, below, above)
        self._n_clipped = n_clipped

        if self._strategy == "flag":
            out["_outlier_flag"] = False
            for col in self._schema.NUMERIC:
                if col not in out.columns:
                    continue
                try:
                    low, high = self._bounds.get_bounds_for_column(col)
                except KeyError:
                    continue
                if low is None or high is None:
                    continue
                out["_outlier_flag"] = out["_outlier_flag"] | (out[col] < low) | (out[col] > high)
            # After flagging, we still clip for modeling
            for col in self._schema.NUMERIC:
                if col in out.columns:
                    try:
                        low, high = self._bounds.get_bounds_for_column(col)
                        if low is not None and high is not None:
                            out[col] = out[col].clip(lower=low, upper=high)
                    except KeyError:
                        pass

        if self._strategy == "remove":
            mask = pd.Series(True, index=out.index)
            for col in self._schema.NUMERIC:
                if col not in out.columns:
                    continue
                try:
                    low, high = self._bounds.get_bounds_for_column(col)
                    if low is None or high is None:
                        continue
                    mask = mask & (out[col] >= low) & (out[col] <= high)
                except KeyError:
                    continue
            before = len(out)
            out = out[mask]
            self._n_removed = before - len(out)
            logger.info("OutlierHandler removed %s rows", self._n_removed)

        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    @property
    def n_clipped(self) -> int:
        return self._n_clipped or 0

    @property
    def n_removed(self) -> int:
        return self._n_removed or 0
