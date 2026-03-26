"""5. Model training — tabular classifiers."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso, LogisticRegression, Ridge

from smart_sensor_ml import config

logger = logging.getLogger(__name__)


def _safe_import_xgb():
    try:
        import xgboost as xgb

        return xgb
    except Exception:
        return None


def _safe_import_lgbm():
    try:
        import lightgbm as lgb

        return lgb
    except Exception:
        return None


def list_model_names() -> List[str]:
    """
    Models to train in batch runs.

    LightGBM is off by default: importing it can hard-fail on some Windows/Python builds.
    Set SMART_SENSOR_TRY_LGBM=1 to attempt LightGBM. XGBoost is attempted unless SMART_SENSOR_TRY_XGB=0.
    """
    names = [
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
    ]
    if os.environ.get("SMART_SENSOR_TRY_XGB", "1") == "1" and _safe_import_xgb() is not None:
        names.append("xgboost")
    if os.environ.get("SMART_SENSOR_TRY_LGBM", "0") == "1" and _safe_import_lgbm() is not None:
        names.append("lightgbm")
    return names


def list_regression_model_names() -> List[str]:
    """Regressors for insulin dose (continuous)."""
    names = [
        "ridge",
        "lasso",
        "elastic_net",
        "random_forest",
        "gradient_boosting",
    ]
    if os.environ.get("SMART_SENSOR_TRY_XGB", "1") == "1" and _safe_import_xgb() is not None:
        names.append("xgboost")
    if os.environ.get("SMART_SENSOR_TRY_LGBM", "0") == "1" and _safe_import_lgbm() is not None:
        names.append("lightgbm")
    return names


def _build_estimator(name: str, random_state: int) -> Any:
    """Construct a single estimator without importing optional broken DLLs unless selected."""
    if name == "logistic_regression":
        return LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=random_state,
        )
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )
    if name == "gradient_boosting":
        return GradientBoostingClassifier(random_state=random_state, max_depth=4, n_estimators=120)
    if name == "xgboost":
        xgb = _safe_import_xgb()
        if xgb is None:
            raise ImportError("xgboost not available")
        return xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=random_state,
            n_jobs=-1,
            eval_metric="mlogloss",
            tree_method="hist",
        )
    if name == "lightgbm":
        lgb = _safe_import_lgbm()
        if lgb is None:
            raise ImportError("lightgbm not available")
        return lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=-1,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=random_state,
            n_jobs=-1,
            class_weight="balanced",
            verbose=-1,
        )
    raise ValueError(f"Unknown model: {name}")


def _build_regression_estimator(name: str, random_state: int) -> Any:
    if name == "ridge":
        return Ridge(alpha=1.0)
    if name == "lasso":
        return Lasso(alpha=0.1, max_iter=5000, random_state=random_state)
    if name == "elastic_net":
        return ElasticNet(alpha=0.05, l1_ratio=0.5, max_iter=5000, random_state=random_state)
    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=250,
            max_depth=14,
            min_samples_leaf=4,
            random_state=random_state,
            n_jobs=-1,
        )
    if name == "gradient_boosting":
        return GradientBoostingRegressor(random_state=random_state, max_depth=4, n_estimators=180, learning_rate=0.06)
    if name == "xgboost":
        xgb = _safe_import_xgb()
        if xgb is None:
            raise ImportError("xgboost not available")
        return xgb.XGBRegressor(
            n_estimators=220,
            max_depth=6,
            learning_rate=0.07,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=random_state,
            n_jobs=-1,
            tree_method="hist",
        )
    if name == "lightgbm":
        lgb = _safe_import_lgbm()
        if lgb is None:
            raise ImportError("lightgbm not available")
        return lgb.LGBMRegressor(
            n_estimators=220,
            max_depth=-1,
            learning_rate=0.06,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        )
    raise ValueError(f"Unknown regression model: {name}")


def train_model(
    name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    random_state: Optional[int] = None,
) -> Any:
    """Train a single model by name."""
    rs = random_state if random_state is not None else config.RANDOM_STATE
    est = _build_estimator(name, rs)
    est.fit(X_train, y_train)
    logger.info("Trained %s on %s samples", name, len(y_train))
    return est


def train_all_tabular(
    X_train: np.ndarray,
    y_train: np.ndarray,
    random_state: Optional[int] = None,
) -> Dict[str, Any]:
    """Train every model returned by list_model_names()."""
    rs = random_state if random_state is not None else config.RANDOM_STATE
    fitted: Dict[str, Any] = {}
    for name in list_model_names():
        try:
            fitted[name] = train_model(name, X_train, y_train, random_state=rs)
        except Exception as e:
            logger.warning("Skipping %s: %s", name, e)
    return fitted


def train_regression_model(
    name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    random_state: Optional[int] = None,
) -> Any:
    rs = random_state if random_state is not None else config.RANDOM_STATE
    est = _build_regression_estimator(name, rs)
    est.fit(X_train, y_train)
    logger.info("Trained %s regressor on %s samples", name, len(y_train))
    return est


def train_all_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
    random_state: Optional[int] = None,
) -> Dict[str, Any]:
    rs = random_state if random_state is not None else config.RANDOM_STATE
    fitted: Dict[str, Any] = {}
    for name in list_regression_model_names():
        try:
            fitted[name] = train_regression_model(name, X_train, y_train, random_state=rs)
        except Exception as e:
            logger.warning("Skipping %s: %s", name, e)
    return fitted
