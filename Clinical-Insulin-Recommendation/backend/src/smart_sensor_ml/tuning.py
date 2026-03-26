"""Hyperparameter tuning with grouped CV (no patient leakage)."""
from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np
from scipy.stats import loguniform, randint, uniform
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso, LogisticRegression, Ridge
from sklearn.model_selection import GroupKFold, RandomizedSearchCV, StratifiedGroupKFold

from smart_sensor_ml import config
from smart_sensor_ml.train_model import _build_regression_estimator, _safe_import_lgbm, _safe_import_xgb

logger = logging.getLogger(__name__)


def _cv_splitter(random_state: int, n_splits: Optional[int] = None) -> StratifiedGroupKFold:
    n_splits = n_splits or config.TUNING_CV_FOLDS
    return StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)


def tune_estimator(
    name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups: np.ndarray,
    random_state: int,
    n_iter: Optional[int] = None,
) -> Any:
    """
    RandomizedSearchCV with StratifiedGroupKFold; same folds for all models (reproducible).
    """
    n_iter = n_iter or config.TUNING_N_ITER
    rs = random_state
    cv = _cv_splitter(rs)
    n_unique = len(np.unique(groups))
    if n_unique < cv.n_splits:
        cv = _cv_splitter(rs, n_splits=max(2, min(3, n_unique)))

    if name == "logistic_regression":
        param_dist = {
            "C": loguniform(1e-3, 1e2),
            "solver": ["lbfgs", "saga"],
        }
        est = LogisticRegression(max_iter=4000, class_weight="balanced", random_state=rs, penalty="l2")
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=min(n_iter, 24),
            cv=cv,
            scoring="accuracy",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned logistic_regression: best CV acc=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "random_forest":
        param_dist = {
            "n_estimators": randint(150, 450),
            "max_depth": [8, 10, 12, 16, 20, None],
            "min_samples_split": randint(2, 20),
            "min_samples_leaf": randint(1, 12),
        }
        est = RandomForestClassifier(class_weight="balanced", random_state=rs, n_jobs=-1)
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="accuracy",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned random_forest: best CV acc=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "gradient_boosting":
        param_dist = {
            "n_estimators": randint(100, 350),
            "max_depth": randint(2, 8),
            "learning_rate": uniform(0.03, 0.2),
            "subsample": uniform(0.65, 0.3),
            "min_samples_leaf": randint(1, 16),
        }
        est = GradientBoostingClassifier(random_state=rs)
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="accuracy",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned gradient_boosting: best CV acc=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "xgboost":
        xgb = _safe_import_xgb()
        if xgb is None:
            from smart_sensor_ml.train_model import _build_estimator

            return _build_estimator(name, rs)
        param_dist = {
            "n_estimators": randint(150, 500),
            "max_depth": randint(3, 12),
            "learning_rate": loguniform(0.01, 0.2),
            "subsample": uniform(0.6, 0.35),
            "colsample_bytree": uniform(0.6, 0.35),
            "min_child_weight": randint(1, 10),
            "reg_alpha": loguniform(1e-4, 1.0),
            "reg_lambda": loguniform(1e-3, 10.0),
        }
        est = xgb.XGBClassifier(
            random_state=rs,
            n_jobs=-1,
            eval_metric="mlogloss",
            tree_method="hist",
        )
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="accuracy",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned xgboost: best CV acc=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "lightgbm":
        lgb = _safe_import_lgbm()
        if lgb is None:
            from smart_sensor_ml.train_model import _build_estimator

            return _build_estimator(name, rs)
        param_dist = {
            "n_estimators": randint(150, 450),
            "max_depth": randint(4, 16),
            "learning_rate": loguniform(0.01, 0.2),
            "subsample": uniform(0.65, 0.3),
            "colsample_bytree": uniform(0.65, 0.3),
            "reg_alpha": loguniform(1e-4, 1.0),
            "reg_lambda": loguniform(1e-3, 10.0),
            "num_leaves": randint(31, 127),
        }
        est = lgb.LGBMClassifier(
            random_state=rs,
            n_jobs=-1,
            class_weight="balanced",
            verbose=-1,
        )
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="accuracy",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned lightgbm: best CV acc=%.4f", search.best_score_)
        return search.best_estimator_

    raise ValueError(f"Unknown model for tuning: {name}")


def _reg_cv_splitter(n_splits: Optional[int] = None) -> GroupKFold:
    n_splits = n_splits or config.TUNING_CV_FOLDS
    return GroupKFold(n_splits=n_splits)


def tune_regression_estimator(
    name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups: np.ndarray,
    random_state: int,
    n_iter: Optional[int] = None,
) -> Any:
    """RandomizedSearchCV with GroupKFold; optimize neg_root_mean_squared_error."""
    n_iter = n_iter or config.TUNING_N_ITER
    rs = random_state
    cv = _reg_cv_splitter()
    n_unique = len(np.unique(groups))
    if n_unique < cv.n_splits:
        cv = _reg_cv_splitter(n_splits=max(2, min(3, n_unique)))

    if name == "ridge":
        param_dist = {"alpha": loguniform(1e-3, 1e3)}
        est = Ridge()
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=min(n_iter, 24),
            cv=cv,
            scoring="neg_root_mean_squared_error",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned ridge: best CV neg_RMSE=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "lasso":
        param_dist = {"alpha": loguniform(1e-4, 10.0)}
        est = Lasso(max_iter=8000, random_state=rs)
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=min(n_iter, 24),
            cv=cv,
            scoring="neg_root_mean_squared_error",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned lasso: best CV neg_RMSE=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "elastic_net":
        param_dist = {"alpha": loguniform(1e-4, 5.0), "l1_ratio": uniform(0.1, 0.8)}
        est = ElasticNet(max_iter=8000, random_state=rs)
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="neg_root_mean_squared_error",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned elastic_net: best CV neg_RMSE=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "random_forest":
        param_dist = {
            "n_estimators": randint(150, 450),
            "max_depth": [8, 10, 12, 16, 20, None],
            "min_samples_split": randint(2, 20),
            "min_samples_leaf": randint(1, 12),
        }
        est = RandomForestRegressor(random_state=rs, n_jobs=-1)
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="neg_root_mean_squared_error",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned random_forest: best CV neg_RMSE=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "gradient_boosting":
        param_dist = {
            "n_estimators": randint(100, 350),
            "max_depth": randint(2, 8),
            "learning_rate": uniform(0.03, 0.2),
            "subsample": uniform(0.65, 0.3),
            "min_samples_leaf": randint(1, 16),
        }
        est = GradientBoostingRegressor(random_state=rs)
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="neg_root_mean_squared_error",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned gradient_boosting: best CV neg_RMSE=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "xgboost":
        xgb = _safe_import_xgb()
        if xgb is None:
            return _build_regression_estimator(name, rs)
        param_dist = {
            "n_estimators": randint(150, 500),
            "max_depth": randint(3, 12),
            "learning_rate": loguniform(0.01, 0.2),
            "subsample": uniform(0.6, 0.35),
            "colsample_bytree": uniform(0.6, 0.35),
            "min_child_weight": randint(1, 10),
            "reg_alpha": loguniform(1e-4, 1.0),
            "reg_lambda": loguniform(1e-3, 10.0),
        }
        est = xgb.XGBRegressor(
            random_state=rs,
            n_jobs=-1,
            tree_method="hist",
        )
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="neg_root_mean_squared_error",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned xgboost: best CV neg_RMSE=%.4f", search.best_score_)
        return search.best_estimator_

    if name == "lightgbm":
        lgb = _safe_import_lgbm()
        if lgb is None:
            return _build_regression_estimator(name, rs)
        param_dist = {
            "n_estimators": randint(150, 450),
            "max_depth": randint(4, 16),
            "learning_rate": loguniform(0.01, 0.2),
            "subsample": uniform(0.65, 0.3),
            "colsample_bytree": uniform(0.65, 0.3),
            "reg_alpha": loguniform(1e-4, 1.0),
            "reg_lambda": loguniform(1e-3, 10.0),
            "num_leaves": randint(31, 127),
        }
        est = lgb.LGBMRegressor(
            random_state=rs,
            n_jobs=-1,
            verbose=-1,
        )
        search = RandomizedSearchCV(
            est,
            param_distributions=param_dist,
            n_iter=n_iter,
            cv=cv,
            scoring="neg_root_mean_squared_error",
            random_state=rs,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train, groups=groups)
        logger.info("Tuned lightgbm: best CV neg_RMSE=%.4f", search.best_score_)
        return search.best_estimator_

    raise ValueError(f"Unknown regression model for tuning: {name}")


def train_tune_all_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups: np.ndarray,
    random_state: int,
) -> Dict[str, Any]:
    from smart_sensor_ml.train_model import list_regression_model_names, train_regression_model

    fitted: Dict[str, Any] = {}
    for name in list_regression_model_names():
        try:
            fitted[name] = tune_regression_estimator(name, X_train, y_train, groups, random_state=random_state)
        except Exception as e:
            logger.warning("Tuning failed for %s, using base estimator: %s", name, e)
            try:
                fitted[name] = train_regression_model(name, X_train, y_train, random_state=random_state)
            except Exception as e2:
                logger.warning("Skipping %s: %s", name, e2)
    return fitted


def train_tune_all_tabular(
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups: np.ndarray,
    random_state: int,
) -> Dict[str, Any]:
    """Tune each model in list_model_names(); skip failed models."""
    from smart_sensor_ml.train_model import list_model_names

    fitted: Dict[str, Any] = {}
    for name in list_model_names():
        try:
            fitted[name] = tune_estimator(name, X_train, y_train, groups, random_state=random_state)
        except Exception as e:
            logger.warning("Tuning failed for %s, using base estimator: %s", name, e)
            try:
                from smart_sensor_ml.train_model import train_model

                fitted[name] = train_model(name, X_train, y_train, random_state=random_state)
            except Exception as e2:
                logger.warning("Skipping %s: %s", name, e2)
    return fitted
