from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from ..config.schema import DataSchema, FeatureEngineeringConfig

class AggregateFeatureCreator:
    def __init__(self, schema: Optional[DataSchema] = None, config: Optional[FeatureEngineeringConfig] = None):
        self._schema = schema or DataSchema()
        self._config = config or FeatureEngineeringConfig()
        self._stats = {}
        self._aggregates = []
        self._created_columns = []

    def fit(self, df: pd.DataFrame):
        self._stats = {}
        self._aggregates = []
        self._created_columns = []
        for agg_name, weight_list in self._config.AGGREGATE_WEIGHTS:
            cols = [c for c, _ in weight_list if c in df.columns]
            if not cols:
                continue
            for col in cols:
                if col not in self._stats:
                    self._stats[col] = {"mean": float(df[col].mean()), "std": float(df[col].std()) or 1.0}
            weights = [(c, w) for c, w in weight_list if c in df.columns]
            if weights:
                self._aggregates.append((agg_name, weights))
                self._created_columns.append(agg_name)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for agg_name, weight_list in self._aggregates:
            total = np.zeros(len(df))
            for col, w in weight_list:
                mean = self._stats[col]["mean"]
                std = self._stats[col]["std"]
                total += w * (out[col].values - mean) / std
            out[agg_name] = total
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    @property
    def aggregate_columns(self) -> List[str]:
        return list(self._created_columns)
