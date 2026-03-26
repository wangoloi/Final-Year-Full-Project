"""
Hyperparameter tuning with Grid Search, Random Search, and optional Optuna.

Provides structured search with stratified CV and configurable scoring.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold

from .config import TuningConfig

logger = logging.getLogger(__name__)


def create_cv(
    n_splits: int = 5,
    shuffle: bool = True,
    random_state: int = 42,
    stratify: Optional[np.ndarray] = None,
) -> StratifiedKFold:
    """Create StratifiedKFold cross-validator."""
    return StratifiedKFold(
        n_splits=n_splits,
        shuffle=shuffle,
        random_state=random_state,
    )


def tune_model(
    estimator: Any,
    param_grid: Dict[str, List[Any]],
    X: np.ndarray,
    y: np.ndarray,
    config: Optional[TuningConfig] = None,
    sample_weight: Optional[np.ndarray] = None,
) -> Tuple[Any, Dict[str, Any], float]:
    """
    Tune hyperparameters via grid or random search.

    Args:
        estimator: Base sklearn-compatible estimator.
        param_grid: Parameter grid (same format for both).
        X: Feature matrix.
        y: Target labels.
        config: Tuning configuration.
        sample_weight: Optional sample weights (e.g. for XGBoost).

    Returns:
        (best_estimator, best_params, best_cv_score)
    """
    cfg = config or TuningConfig()
    cv = create_cv(
        n_splits=cfg.cv_folds,
        shuffle=True,
        random_state=cfg.random_state,
    )

    n_combinations = 1
    for v in param_grid.values():
        n_combinations *= len(v)

    if cfg.search_type == "grid" or n_combinations <= cfg.random_search_n_iter:
        search = GridSearchCV(
            estimator,
            param_grid=param_grid,
            cv=cv,
            scoring=cfg.scoring,
            n_jobs=cfg.n_jobs,
            refit=True,
        )
    else:
        n_iter = min(cfg.random_search_n_iter, n_combinations)
        search = RandomizedSearchCV(
            estimator,
            param_distributions=param_grid,
            n_iter=n_iter,
            cv=cv,
            scoring=cfg.scoring,
            n_jobs=cfg.n_jobs,
            random_state=cfg.random_state,
            refit=True,
        )

    fit_params = {}
    if sample_weight is not None:
        fit_params["sample_weight"] = sample_weight

    if fit_params:
        search.fit(X, y, **fit_params)
    else:
        search.fit(X, y)

    return search.best_estimator_, dict(search.best_params_), float(search.best_score_)


def try_optuna_tune(
    estimator: Any,
    param_distributions: Dict[str, Any],
    X: np.ndarray,
    y: np.ndarray,
    config: Optional[TuningConfig] = None,
) -> Optional[Tuple[Any, Dict[str, Any], float]]:
    """
    Optional Optuna-based tuning. Returns None if Optuna not installed.

    param_distributions: Dict of param_name -> optuna.distributions (e.g. Categorical, Float).
    """
    try:
        import optuna
        from optuna.samplers import TPESampler
    except ImportError:
        logger.debug("Optuna not installed; skipping Optuna tuning")
        return None

    cfg = config or TuningConfig()
    cv = create_cv(n_splits=cfg.cv_folds, shuffle=True, random_state=cfg.random_state)

    def objective(trial):
        params = {}
        for name, dist in param_distributions.items():
            if hasattr(dist, "suggest"):
                params[name] = dist.suggest(trial)
            elif isinstance(dist, (list, tuple)):
                params[name] = trial.suggest_categorical(name, list(dist))
            elif isinstance(dist, dict) and "low" in dist and "high" in dist:
                log = dist.get("log", False)
                params[name] = trial.suggest_float(name, dist["low"], dist["high"], log=log)
            else:
                params[name] = dist
        est = __import__("sklearn.base", fromlist=["clone"]).clone(estimator)
        est.set_params(**params)
        from sklearn.model_selection import cross_val_score
        scores = cross_val_score(est, X, y, cv=cv, scoring=cfg.scoring, n_jobs=1)
        return scores.mean()

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=cfg.random_state))
    study.optimize(
        objective,
        n_trials=cfg.optuna_n_trials,
        timeout=cfg.optuna_timeout,
        show_progress_bar=False,
    )
    best_params = study.best_params
    best_estimator = __import__("sklearn.base", fromlist=["clone"]).clone(estimator)
    best_estimator.set_params(**best_params)
    best_estimator.fit(X, y)
    return best_estimator, best_params, float(study.best_value)
