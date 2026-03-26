"""Interaction feature creator: product features from pairs (e.g. glucose x insulin_sensitivity)."""
from typing import List, Optional, Tuple
import pandas as pd
from ..config.schema import DataSchema, FeatureEngineeringConfig


class InteractionFeatureCreator:
    def __init__(self, schema: Optional[DataSchema] = None, config: Optional[FeatureEngineeringConfig] = None):
        self._schema = schema or DataSchema()
        self._config = config or FeatureEngineeringConfig()
        self._pairs = []
        self._created_columns = []

    def fit(self, df: pd.DataFrame):
        available = set(df.columns)
        self._pairs = []
        for a, b in self._config.INTERACTION_PAIRS:
            if a in available and b in available:
                self._pairs.append((a, b))
        self._created_columns = [f"{a}_{b}_interaction" for a, b in self._pairs]
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for (a, b), name in zip(self._pairs, self._created_columns):
            out[name] = out[a] * out[b]
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    @property
    def interaction_columns(self) -> List[str]:
        return list(self._created_columns)