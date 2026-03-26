from typing import List, Optional
import pandas as pd
from ..config.schema import DataSchema, FeatureEngineeringConfig

class PolynomialFeatureCreator:
    def __init__(self, schema: Optional[DataSchema] = None, config: Optional[FeatureEngineeringConfig] = None):
        self._schema = schema or DataSchema()
        self._config = config or FeatureEngineeringConfig()
        self._columns = []
        self._scale = {}
        self._created_columns = []

    def fit(self, df: pd.DataFrame):
        available = set(df.columns)
        self._columns = [c for c in self._config.POLYNOMIAL_COLUMNS if c in available]
        self._scale = {}
        self._created_columns = []
        for col in self._columns:
            s = df[col].std()
            self._scale[col] = float(s) if s and s > 1e-8 else 1.0
            self._created_columns.append(f"{col}_poly2")
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for col in self._columns:
            scale = self._scale.get(col, 1.0)
            out[f"{col}_poly2"] = (out[col] / scale) ** 2
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    @property
    def polynomial_columns(self) -> List[str]:
        return list(self._created_columns)
