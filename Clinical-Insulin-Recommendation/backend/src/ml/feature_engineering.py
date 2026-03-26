"""
Enhanced feature engineering with derived, interaction, polynomial, aggregate,
trend-based, and statistical features.

Includes Recursive Feature Elimination (RFE) support.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_selection import (
    SelectKBest,
    mutual_info_classif,
    f_classif,
    RFECV,
    VarianceThreshold,
)

from .config import FeatureConfig
from ..insulin_system.config.schema import DataSchema
from ..insulin_system.data_processing.feature_engineering import (
    FeatureEngineer,
    DERIVED_CATEGORICAL,
    DERIVED_NUMERIC_BASE,
    CONTEXTUAL_NUMERIC,
)
from ..insulin_system.data_processing.interaction_features import InteractionFeatureCreator
from ..insulin_system.data_processing.polynomial_features import PolynomialFeatureCreator
from ..insulin_system.data_processing.aggregate_features import AggregateFeatureCreator
from ..insulin_system.data_processing.temporal_features import TemporalFeatureCreator
from ..insulin_system.config.schema import FeatureEngineeringConfig

logger = logging.getLogger(__name__)


def _make_fe_config(config: FeatureConfig) -> FeatureEngineeringConfig:
    """Convert FeatureConfig to FeatureEngineeringConfig."""
    default_agg = (
        ("metabolic_risk_score", (("glucose_level", 0.4), ("HbA1c", 0.35), ("BMI", 0.25))),
        ("glycemic_burden", (("glucose_level", 0.5), ("HbA1c", 0.5))),
    )
    return FeatureEngineeringConfig(
        INTERACTION_PAIRS=config.interaction_pairs,
        POLYNOMIAL_COLUMNS=config.polynomial_columns,
        POLYNOMIAL_DEGREE=config.polynomial_degree,
        AGGREGATE_WEIGHTS=default_agg,
        SELECTION_METHOD=config.selection_method,
        SELECTION_K=config.selection_k,
        VARIANCE_THRESHOLD=config.variance_threshold,
        DOMAIN_KEEP=config.domain_keep,
        TEMPORAL_ORDER_COLUMN=config.temporal_order_column,
    )


def add_glucose_zone_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add numeric glucose zone (0=hypo, 1=low-normal, 2=target, 3=mild hyper, 4=moderate, 5=severe).
    More interpretable than glucose_risk categorical.
    """
    out = df.copy()
    if "glucose_level" not in out.columns:
        return out
    gl = out["glucose_level"]
    out["glucose_zone_numeric"] = np.select(
        [gl < 70, gl < 100, gl < 130, gl < 180, gl < 250, True],
        [0, 1, 2, 3, 4, 5],
        default=2,
    ).astype(np.float64)
    return out


class EnhancedFeatureEngineer:
    """
    Extended feature engineering: base FeatureEngineer + glucose_zone_numeric + iob_carbs.
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        self._config = config or FeatureConfig()
        self._fe_config = _make_fe_config(self._config)
        self._base_engineer = FeatureEngineer(schema=DataSchema(), config=self._fe_config)

    def fit(self, df: pd.DataFrame) -> "EnhancedFeatureEngineer":
        self._base_engineer.fit(df)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self._base_engineer.transform(df)
        out = add_glucose_zone_numeric(out)
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)


class FeatureSelectorRFE:
    """
    Feature selection with optional RFE (Recursive Feature Elimination).

    Supports: mutual_info, f_classif, rfe, none.
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        self._config = config or FeatureConfig()
        self._variance_selector = None
        self._stat_selector = None
        self._rfe_estimator = None
        self._domain_cols: List[str] = []
        self._selected_names: List[str] = []
        self._fitted = False

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        estimator=None,
    ) -> "FeatureSelectorRFE":
        cols = list(X.columns)
        y_arr = np.asarray(y)

        if self._config.selection_method == "none":
            self._selected_names = cols
            self._fitted = True
            return self

        domain_keep = set(self._config.domain_keep)
        self._domain_cols = [c for c in cols if not domain_keep or any(k in c for k in domain_keep)]
        if not self._domain_cols:
            self._domain_cols = cols

        X_arr = X[self._domain_cols].values.astype(np.float64, copy=False)
        self._variance_selector = VarianceThreshold(threshold=self._config.variance_threshold)
        X_arr = self._variance_selector.fit_transform(X_arr)
        cols_after_var = [c for c, s in zip(self._domain_cols, self._variance_selector.get_support()) if s]

        if self._config.selection_method == "rfe" and estimator is not None and cols_after_var:
            from sklearn.ensemble import RandomForestClassifier
            rf = estimator or RandomForestClassifier(n_estimators=50, random_state=42)
            self._rfe_estimator = RFECV(
                estimator=rf,
                step=1,
                cv=3,
                scoring="f1_weighted",
                n_jobs=1,
            )
            self._rfe_estimator.fit(X_arr, y_arr)
            support = self._rfe_estimator.support_
            self._selected_names = [c for c, s in zip(cols_after_var, support) if s]
        elif self._config.selection_method in ("mutual_info", "f_classif") and cols_after_var:
            k = self._config.selection_k or len(cols_after_var)
            k = min(k, X_arr.shape[1], max(1, X_arr.shape[0] - 1))
            if self._config.selection_method == "mutual_info":
                self._stat_selector = SelectKBest(mutual_info_classif, k=k)
            else:
                self._stat_selector = SelectKBest(f_classif, k=k)
            self._stat_selector.fit(X_arr, y_arr)
            support = self._stat_selector.get_support()
            self._selected_names = [c for c, s in zip(cols_after_var, support) if s]
        else:
            self._selected_names = cols_after_var

        self._fitted = True
        logger.info("FeatureSelector selected %s features", len(self._selected_names))
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("FeatureSelector must be fitted before transform")
        X_arr = X[self._domain_cols].values.astype(np.float64, copy=False)
        X_arr = self._variance_selector.transform(X_arr)
        if self._stat_selector is not None:
            X_arr = self._stat_selector.transform(X_arr)
        elif self._rfe_estimator is not None:
            X_arr = self._rfe_estimator.transform(X_arr)
        return pd.DataFrame(X_arr, columns=self._selected_names, index=X.index)

    @property
    def selected_features(self) -> List[str]:
        return list(self._selected_names)
