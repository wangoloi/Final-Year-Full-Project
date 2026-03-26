"""
Model definitions: baseline and advanced classifiers with default params and search grids.
"""

from typing import Any, Dict, List, Tuple

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.neural_network import MLPClassifier

# Baseline
BASELINE_MODELS = [
    "logistic_regression",
    "decision_tree",
    "random_forest",
]
# Advanced
ADVANCED_MODELS = [
    "gradient_boosting",
    "mlp",
    "rnn_lstm",
]
# Ensemble
STACKING_MODEL = "stacking_ensemble"

MODEL_NAMES = BASELINE_MODELS + ADVANCED_MODELS


def _lr_params() -> Tuple[Any, Dict[str, List[Any]]]:
    est = LogisticRegression(
        penalty="l2",
        max_iter=5000,
        random_state=42,
        class_weight="balanced",
    )
    grid = {
        "C": [0.01, 0.1, 1.0, 10.0],
        "solver": ["lbfgs", "saga"],
    }
    return est, grid


def _dt_params() -> Tuple[Any, Dict[str, List[Any]]]:
    est = DecisionTreeClassifier(random_state=42, class_weight="balanced")
    grid = {
        "max_depth": [3, 5, 7],
        "min_samples_split": [5, 10, 20],
        "min_samples_leaf": [4, 8, 16],
        "ccp_alpha": [0.001, 0.01, 0.1],
    }
    return est, grid


def _rf_params() -> Tuple[Any, Dict[str, List[Any]]]:
    est = RandomForestClassifier(random_state=42, class_weight="balanced")
    grid = {
        "n_estimators": [100, 200],
        "max_depth": [8, 12, 15],
        "min_samples_split": [5, 10],
        "min_samples_leaf": [2, 4],
    }
    return est, grid


def _gb_params() -> Tuple[Any, Dict[str, List[Any]]]:
    try:
        import xgboost as xgb
        kwargs = {"objective": "multi:softmax", "num_class": 4, "random_state": 42}
        if hasattr(xgb.XGBClassifier, "use_label_encoder"):
            kwargs["use_label_encoder"] = False
            kwargs["eval_metric"] = "mlogloss"
        est = xgb.XGBClassifier(**kwargs)
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        est = GradientBoostingClassifier(random_state=42)
    grid = {
        "n_estimators": [100, 200],
        "max_depth": [3, 5],
        "learning_rate": [0.01, 0.05],
        "subsample": [0.8],
        "colsample_bytree": [0.8] if "colsample_bytree" in dir(est) else [],
    }
    if not hasattr(est, "colsample_bytree"):
        grid = {k: v for k, v in grid.items() if k != "colsample_bytree"}
    return est, grid


def _mlp_params() -> Tuple[Any, Dict[str, List[Any]]]:
    est = MLPClassifier(random_state=42, max_iter=500, early_stopping=True)
    grid = {
        "hidden_layer_sizes": [(64,), (64, 32)],
        "alpha": [0.001, 0.01],
        "learning_rate_init": [0.001],
    }
    return est, grid


def _rnn_params() -> Tuple[Any, Dict[str, List[Any]]]:
    """RNN/LSTM uses custom training in ModelTrainer; placeholder for get_model_definitions."""
    return None, {}  # type: ignore


def _stacking_params() -> Tuple[Any, Dict[str, List[Any]]]:
    """Stacking ensemble: RF + GB + LR as base, LR as meta-learner."""
    try:
        import xgboost as xgb
        gb = xgb.XGBClassifier(objective="multi:softmax", num_class=4, random_state=42, use_label_encoder=False, eval_metric="mlogloss")
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        gb = GradientBoostingClassifier(random_state=42)
    estimators = [
        ("rf", RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight="balanced")),
        ("gb", gb),
        ("lr", LogisticRegression(max_iter=2000, random_state=42, class_weight="balanced")),
    ]
    est = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=5000, solver="lbfgs", class_weight="balanced", random_state=42),
        cv=3,
    )
    grid = {"final_estimator__C": [0.1, 1.0, 10.0]}  # Minimal grid for meta-learner
    return est, grid


def get_model_definitions(exclude_mlp: bool = False, include_rnn: bool = True, include_stacking: bool = False) -> Dict[str, Tuple[Any, Dict[str, List[Any]]]]:
    """Return dict of model_name -> (estimator, param_grid).
    exclude_mlp: If True, omit MLP (per revised pipeline for clinically interpretable models).
    include_rnn: If True, include RNN/LSTM (uses custom training path).
    include_stacking: If True, include stacking ensemble.
    """
    all_models = {
        "logistic_regression": _lr_params(),
        "decision_tree": _dt_params(),
        "random_forest": _rf_params(),
        "gradient_boosting": _gb_params(),
        "mlp": _mlp_params(),
        "rnn_lstm": _rnn_params(),
        "stacking_ensemble": _stacking_params(),
    }
    if exclude_mlp:
        all_models = {k: v for k, v in all_models.items() if k != "mlp"}
    if not include_rnn:
        all_models = {k: v for k, v in all_models.items() if k != "rnn_lstm"}
    if not include_stacking:
        all_models = {k: v for k, v in all_models.items() if k != "stacking_ensemble"}
    return all_models
