from typing import List, Optional
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from ..config.schema import DataSchema


class CategoricalEncoder:
    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        drop_first: bool = True,
        extra_categorical_columns: Optional[List[str]] = None,
    ):
        self._schema = schema or DataSchema()
        self._drop_first = drop_first
        self._extra = list(extra_categorical_columns or [])
        self._encoder = None
        self._encoded_columns = []
        self._fitted_cat_cols = []

    def fit(self, df: pd.DataFrame):
        base = [c for c in self._schema.CATEGORICAL if c in df.columns]
        extra = [c for c in self._extra if c in df.columns]
        cat_cols = base + extra
        if not cat_cols:
            self._encoder = None
            return self
        self._encoder = OneHotEncoder(
            drop="first" if self._drop_first else None,
            handle_unknown="ignore",
            sparse_output=False,
        )
        self._encoder.fit(df[cat_cols])
        self._fitted_cat_cols = cat_cols
        self._encoded_columns = self._encoder.get_feature_names_out(cat_cols).tolist()
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._encoder is None:
            return df.copy()
        cat_cols = [c for c in self._fitted_cat_cols if c in df.columns]
        if len(cat_cols) != len(self._fitted_cat_cols):
            missing = set(self._fitted_cat_cols) - set(cat_cols)
            raise ValueError("Transform missing fitted columns: " + str(missing))
        out = df.drop(columns=cat_cols, errors="ignore")
        encoded = self._encoder.transform(df[self._fitted_cat_cols])
        enc_df = pd.DataFrame(encoded, columns=self._encoded_columns, index=df.index)
        out = pd.concat([out, enc_df], axis=1)
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    @property
    def encoded_feature_names(self) -> List[str]:
        return list(self._encoded_columns)

    @property
    def is_fitted(self) -> bool:
        return self._encoder is not None
