"""
Phase 4: Model definitions with early stopping and overfitting control.

Tree-based focus; LightGBM, CatBoost, XGBoost with advanced tuning.
"""

import logging
from typing import Any, Dict, Tuple

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier

from .config import RANDOM_STATE

logger = logging.getLogger(__name__)


def _xgboost_model(**kwargs) -> Any:
    """XGBoost with early stopping support."""
    try:
        import xgboost as xgb
        return xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=4,
            random_state=RANDOM_STATE,
            use_label_encoder=False,
            eval_metric="mlogloss",
            **kwargs
        )
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        return GradientBoostingClassifier(random_state=RANDOM_STATE, **kwargs)


def _lightgbm_model(**kwargs) -> Any:
    """LightGBM with early stopping."""
    try:
        import lightgbm as lgb
        return lgb.LGBMClassifier(
            objective="multiclass",
            num_class=4,
            random_state=RANDOM_STATE,
            verbose=-1,
            force_col_wise=True,
            **kwargs
        )
    except ImportError:
        return None


def _catboost_model(**kwargs) -> Any:
    """CatBoost with early stopping."""
    try:
        import catboost as cb
        return cb.CatBoostClassifier(
            loss_function="MultiClass",
            random_state=RANDOM_STATE,
            verbose=0,
            **kwargs
        )
    except ImportError:
        return None


def create_model(name: str, **kwargs) -> Any:
    """Create model by name with overfitting controls."""
    if name == "gradient_boosting":
        return _xgboost_model(**kwargs)
    if name == "random_forest":
        return RandomForestClassifier(random_state=RANDOM_STATE, class_weight="balanced", **kwargs)
    if name == "extra_trees":
        return ExtraTreesClassifier(random_state=RANDOM_STATE, class_weight="balanced", **kwargs)
    if name == "balanced_rf":
        try:
            from imblearn.ensemble import BalancedRandomForestClassifier
            return BalancedRandomForestClassifier(random_state=RANDOM_STATE, **kwargs)
        except ImportError:
            return RandomForestClassifier(random_state=RANDOM_STATE, class_weight="balanced", **kwargs)
    if name == "lightgbm":
        return _lightgbm_model(**kwargs)
    if name == "catboost":
        return _catboost_model(**kwargs)
    if name == "mlp":
        return MLPClassifier(
            random_state=RANDOM_STATE,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.1,
            **kwargs
        )
    if name == "logistic_regression":
        return LogisticRegression(max_iter=5000, random_state=RANDOM_STATE, class_weight="balanced", **kwargs)
    raise ValueError(f"Unknown model: {name}")


def get_optuna_params(model_name: str, trial) -> Dict[str, Any]:
    """Optuna parameter suggestions per model."""
    if model_name == "gradient_boosting":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 400),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 1.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 1.0, log=True),
        }
    if model_name == "lightgbm":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 400),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 1.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 1.0, log=True),
        }
    if model_name == "catboost":
        return {
            "iterations": trial.suggest_int("iterations", 100, 400),
            "depth": trial.suggest_int("depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-4, 10.0, log=True),
        }
    if model_name == "random_forest":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 300),
            "max_depth": trial.suggest_int("max_depth", 5, 12),
            "min_samples_split": trial.suggest_int("min_samples_split", 5, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 2, 10),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2"]),
        }
    if model_name == "extra_trees":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 300),
            "max_depth": trial.suggest_int("max_depth", 5, 12),
            "min_samples_split": trial.suggest_int("min_samples_split", 5, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 2, 10),
        }
    if model_name == "balanced_rf":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 300),
            "max_depth": trial.suggest_int("max_depth", 5, 12),
        }
    if model_name == "mlp":
        return {
            "hidden_layer_sizes": trial.suggest_categorical("hidden_layer_sizes", [(64,), (64, 32), (128, 64)]),
            "alpha": trial.suggest_float("alpha", 1e-4, 0.1, log=True),
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 0.01, log=True),
        }
    return {}
