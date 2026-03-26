"""
Preprocessing module: imputation, outlier handling, encoding, scaling, and splitting.

Combines all preprocessing steps with configurable strategies.
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

from .config import DataConfig, PreprocessingConfig
from ..insulin_system.config.schema import ClinicalBounds
from ..insulin_system.data_processing.imputation import MissingValueImputer
from ..insulin_system.data_processing.outliers import OutlierHandler
from ..insulin_system.data_processing.encoding import CategoricalEncoder
from ..insulin_system.config.schema import DataSchema, FeatureEngineeringConfig
from .feature_engineering import DERIVED_CATEGORICAL

logger = logging.getLogger(__name__)


def get_scaler(scaler_type: str):
    """Return sklearn scaler by type name."""
    scalers = {
        "standard": StandardScaler,
        "minmax": MinMaxScaler,
        "robust": RobustScaler,
    }
    cls = scalers.get(scaler_type.lower(), StandardScaler)
    return cls()


class Preprocessor:
    """
    End-to-end preprocessor: impute -> outliers -> encode -> scale -> split.

    Fits on training data; transforms train/val/test consistently.
    """

    def __init__(
        self,
        data_config: Optional[DataConfig] = None,
        preprocess_config: Optional[PreprocessingConfig] = None,
    ):
        self._data_cfg = data_config or DataConfig()
        self._prep_cfg = preprocess_config or PreprocessingConfig()
        self._schema = DataSchema()
        self._imputer = MissingValueImputer(
            schema=self._schema,
            numeric_strategy=self._prep_cfg.missing_numeric_strategy,
            categorical_strategy=self._prep_cfg.missing_categorical_strategy,
        )
        self._outlier_handler = OutlierHandler(
            schema=self._schema,
            bounds=ClinicalBounds(),
            strategy=self._prep_cfg.outlier_strategy,
        )
        self._encoder = CategoricalEncoder(
            schema=self._schema,
            drop_first=True,
            extra_categorical_columns=tuple(DERIVED_CATEGORICAL),
        )
        self._scaler = None
        self._scaler_type = self._prep_cfg.scaler_type
        self._fe_config = FeatureEngineeringConfig()
        self._fitted = False

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step. Use for training data."""
        out = self._imputer.fit_transform(df)
        out = self._outlier_handler.fit_transform(out)
        out = self._encoder.fit_transform(out)
        scaler = get_scaler(self._scaler_type)
        numeric_cols = self._get_numeric_columns(out)
        if numeric_cols:
            out[numeric_cols] = scaler.fit_transform(out[numeric_cols].fillna(0))
        self._scaler = scaler
        self._fitted = True
        return out

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform only. Call after fit_transform on train."""
        if not self._fitted:
            raise RuntimeError("Preprocessor must be fitted before transform")
        out = self._imputer.transform(df)
        out = self._outlier_handler.transform(out)
        out = self._encoder.transform(out)
        numeric_cols = self._get_numeric_columns(out)
        if numeric_cols and self._scaler is not None:
            out[numeric_cols] = self._scaler.transform(out[numeric_cols].fillna(0))
        return out

    def _get_numeric_columns(self, df: pd.DataFrame) -> list:
        """Columns that need scaling (numeric, excluding IDs and target)."""
        exclude = {self._schema.PATIENT_ID, self._schema.TARGET, self._schema.TARGET_REGRESSION, "_outlier_flag"}
        from ..insulin_system.data_processing.feature_engineering import FeatureEngineer
        extra = FeatureEngineer.derived_numeric_columns(self._fe_config)
        numeric_base = list(self._schema.NUMERIC) + list(getattr(self._schema, "CONTEXTUAL_NUMERIC", ()))
        numeric_base.extend(extra)
        return [c for c in numeric_base if c in df.columns and c not in exclude]

    def split(
        self,
        df: pd.DataFrame,
        stratify_col: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split into train, validation, and test.

        Args:
            df: Preprocessed DataFrame.
            stratify_col: For random split, column to stratify on (e.g. target).
            sort_by: For temporal split, column to sort by (e.g. patient_id).

        Returns:
            (train_df, val_df, test_df)
        """
        cfg = self._prep_cfg
        if cfg.split_type == "random":
            return self._random_split(df, stratify_col)
        return self._temporal_split(df, sort_by or self._schema.PATIENT_ID)

    def _random_split(
        self,
        df: pd.DataFrame,
        stratify_col: Optional[str],
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        cfg = self._prep_cfg
        stratify = df[stratify_col] if stratify_col and stratify_col in df.columns else None
        train_df, rest = train_test_split(
            df, train_size=cfg.train_ratio, stratify=stratify, random_state=cfg.random_state
        )
        if cfg.val_ratio > 0 and len(rest) > 0:
            stratify_rest = rest[stratify_col] if stratify_col and stratify_col in rest.columns else None
            val_ratio_adj = cfg.val_ratio / (1 - cfg.train_ratio)
            val_df, test_df = train_test_split(
                rest, train_size=val_ratio_adj, stratify=stratify_rest, random_state=cfg.random_state
            )
        else:
            val_df = pd.DataFrame()
            test_df = rest
        logger.info("RandomSplit: train=%s, val=%s, test=%s", len(train_df), len(val_df), len(test_df))
        return train_df, val_df, test_df

    def _temporal_split(
        self,
        df: pd.DataFrame,
        sort_by: str,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        cfg = self._prep_cfg
        data = df.sort_values(by=sort_by) if sort_by in df.columns else df
        n = len(data)
        n_train = int(n * cfg.train_ratio)
        remainder = n - n_train
        n_val = int(remainder * cfg.val_ratio)
        n_test = remainder - n_val
        train_df = data.iloc[:n_train]
        val_df = data.iloc[n_train : n_train + n_val]
        test_df = data.iloc[n_train + n_val :]
        logger.info("TemporalSplit: train=%s, val=%s, test=%s", len(train_df), len(val_df), len(test_df))
        return train_df, val_df, test_df
