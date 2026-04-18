from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd

from ..config.schema import DataSchema
from ..exceptions import DataValidationError


@dataclass
class TemporalSplitter:
    """
    Deterministic split that preserves row order (or a specified sort order).

    Intended for time-ordered datasets where shuffling would leak future into past.
    """

    schema: Optional[DataSchema] = None
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    random_state: int = 42  # kept for API compatibility; not used

    def split(self, df: pd.DataFrame, sort_by: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            raise DataValidationError("Empty dataset")
        if not (0 < self.train_ratio < 1) or not (0 <= self.val_ratio < 1):
            raise DataValidationError("Invalid split ratios")
        if self.train_ratio + self.val_ratio >= 1:
            raise DataValidationError("train_ratio + val_ratio must be < 1")

        out = df.copy()
        if sort_by and sort_by in out.columns:
            out = out.sort_values(by=sort_by, kind="stable").reset_index(drop=True)
        else:
            out = out.reset_index(drop=True)

        n = len(out)
        n_train = int(n * self.train_ratio)
        n_val = int(n * self.val_ratio)
        n_train = max(0, min(n_train, n))
        n_val = max(0, min(n_val, n - n_train))

        train = out.iloc[:n_train].copy()
        val = out.iloc[n_train : n_train + n_val].copy()
        test = out.iloc[n_train + n_val :].copy()
        return train, val, test

