"""
Feature selection using domain knowledge and statistical methods.

Combines domain-based keep/drop with statistical selection (variance,
mutual information, or ANOVA F-value). Fitted on (X, y); transforms X.
"""

import logging
from typing import List, Optional

import pandas as pd
import numpy as np
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif, VarianceThreshold

from ..config.schema import FeatureEngineeringConfig
from ..exceptions import DataValidationError

logger = logging.getLogger(__name__)


class FeatureSelector:
    """
    Domain + statistical feature selection. Fit on (X_train, y_train); transform X_train, X_val, X_test.
    """


    def __init__(self, config: Optional[FeatureEngineeringConfig] = None):
        self._config = config or FeatureEngineeringConfig()
        self._variance_selector = None
        self._stat_selector = None
        self._domain_cols: List[str] = []
        self._selected_names: List[str] = []
        self._corr_keep_indices: Optional[List[int]] = None  # Indices to keep after correlation removal
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "FeatureSelector":
        """Fit variance filter and optional SelectKBest on training data."""
        if X.shape[0] != len(y):
            raise DataValidationError("X and y length mismatch")
        cols = list(X.columns)
        y_arr = np.asarray(y)

        if self._config.SELECTION_METHOD == "none":
            self._selected_names = cols
            self._domain_cols = cols
            self._fitted = True
            return self

        domain_keep = set(self._config.DOMAIN_KEEP)
        domain_drop = set(self._config.DOMAIN_DROP)
        self._domain_cols = [c for c in cols if self._keep_domain(c, domain_keep, domain_drop)]
        if not self._domain_cols:
            self._domain_cols = cols
        X_arr = X[self._domain_cols].values.astype(np.float64, copy=False)

        self._variance_selector = VarianceThreshold(threshold=self._config.VARIANCE_THRESHOLD)
        X_arr = self._variance_selector.fit_transform(X_arr)
        support = self._variance_selector.get_support()
        cols_after_var = [c for c, s in zip(self._domain_cols, support) if s]

        # Phase 2: Remove highly correlated features (threshold 0.95)
        self._corr_keep_indices = None
        if len(cols_after_var) > 2:
            X_df = pd.DataFrame(X_arr, columns=cols_after_var)
            corr = X_df.corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            to_drop = [c for c in upper.columns if any(upper[c] > 0.95)]
            if to_drop:
                cols_after_corr = [c for c in cols_after_var if c not in to_drop]
                self._corr_keep_indices = [cols_after_var.index(c) for c in cols_after_corr]
                cols_after_var = cols_after_corr
                X_arr = X_df.drop(columns=to_drop).values
                logger.info("Removed %s correlated features", len(to_drop))

        if self._config.SELECTION_METHOD in ("mutual_info", "f_classif") and cols_after_var:
            k = self._config.SELECTION_K or len(cols_after_var)
            k = min(k, X_arr.shape[1], max(1, X_arr.shape[0] - 1))
            if self._config.SELECTION_METHOD == "mutual_info":
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

    def _keep_domain(self, col: str, keep: set, drop: set) -> bool:
        if any(d in col for d in drop):
            return False
        if not keep:
            return True
        return any(k in col for k in keep)

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Apply same pipeline: domain cols -> variance -> stat selector -> return DataFrame."""
        if not self._fitted:
            raise DataValidationError("FeatureSelector must be fitted before transform")
        missing = set(self._domain_cols) - set(X.columns)
        if missing:
            raise DataValidationError("Transform missing columns: " + str(missing))
        X_arr = X[self._domain_cols].values.astype(np.float64, copy=False)
        X_arr = self._variance_selector.transform(X_arr)
        if self._corr_keep_indices is not None:
            X_arr = X_arr[:, self._corr_keep_indices]
        if self._stat_selector is not None:
            X_arr = self._stat_selector.transform(X_arr)
        return pd.DataFrame(X_arr, columns=self._selected_names, index=X.index)

    def fit_transform(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        return self.fit(X, y).transform(X)

    @property
    def selected_features(self) -> List[str]:
        return list(self._selected_names)

    @property
    def is_fitted(self) -> bool:
        return self._fitted
