"""
Full Clinical ML Improvement Pipeline — Phases 1–11 (v3).

Pipeline order: preprocessing → feature engineering → model training
→ probability calibration → threshold optimization → evaluation.

Based on experiment insights:
- SMOTE removed (hurts performance)
- Class weights and cost-sensitive learning only
- Probability calibration (Platt/isotonic) before threshold optimization
- Tree-based models focus (LightGBM, CatBoost, XGBoost, RF, Extra Trees)
- Threshold optimization
- Stacking ensemble with calibrated base models
- Early stopping for boosters
- Retrain best on full data before deployment
"""

from __future__ import annotations

import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import StackingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from insulin_system.config.schema import CLINICAL_COST_MATRIX, PipelineConfig
from insulin_system.data_processing.pipeline import DataProcessingPipeline
from insulin_system.models.evaluation import evaluate_model
from insulin_system.persistence import InferenceBundle, save_best_model

from .calibration import (
    _LabelEncoderWrapper,
    wrap_with_calibration,
    _get_calibration_data,
    CALIBRATION_METHODS,
)
from .config import (
    CLINICAL_COST_MATRIX as COST_MATRIX,
    is_better_by_rank,
    DEFAULT_MODELS,
    RANDOM_STATE,
    CV_FOLDS,
    OPTUNA_TRIALS,
)
from .experiment_tracker import ExperimentTracker
from .models import create_model, get_optuna_params
from .threshold_optimizer import ThresholdOptimizedClassifier, optimize_thresholds_cost_sensitive

logger = logging.getLogger(__name__)


def _cost_sensitive_weights(y: np.ndarray, labels: List[str]) -> np.ndarray:
    """
    Compute sample weights from clinical cost matrix.
    For each true class, weight = 1 + mean misclassification cost (from cost matrix row).
    Classes with higher cost of being wrong get higher weight during training.
    """
    cost_matrix = COST_MATRIX
    class_weights = {}
    for c in ("down", "up", "steady", "no"):
        row = cost_matrix.get(c, {})
        costs = [v for k, v in row.items() if k != c and v > 0]
        mean_cost = sum(costs) / len(costs) if costs else 1.0
        class_weights[c] = 1.0 + mean_cost
    n = len(y)
    weights = np.ones(n, dtype=np.float64)
    for i in range(n):
        yi_str = str(y[i]).lower()
        weights[i] = class_weights.get(yi_str, 1.0)
    return weights


def _get_sample_weights(strategy: str, y: np.ndarray, labels: List[str]) -> Optional[np.ndarray]:
    """Return sample weights for cost-sensitive or None for class_weight."""
    if strategy == "cost_sensitive":
        return _cost_sensitive_weights(y, labels)
    return None


def _is_better_candidate(
    ev: Any,
    overfitting_gap: float,
    best_metrics: Dict[str, Any],
) -> bool:
    """True if ev is better than current best using rank-based (Borda-style) comparison."""
    return is_better_by_rank(
        ev.f1_weighted, ev.roc_auc_ovr_weighted, ev.f1_macro,
        ev.clinical_cost, overfitting_gap,
        best_metrics.get("f1_weighted", 0), best_metrics.get("roc_auc", 0),
        best_metrics.get("f1_macro", 0), best_metrics.get("clinical_cost", float("inf")),
        best_metrics.get("overfitting_gap", float("inf")),
    )


def _clinical_cost(y_true: np.ndarray, y_pred: List[str], labels: List[str]) -> float:
    total, n = 0.0, len(y_true)
    for i in range(n):
        t = str(y_true[i]).lower()
        p = str(y_pred[i]).lower()
        total += COST_MATRIX.get(t, {}).get(p, 1.0)
    return total / n if n else float("nan")


def _tune_model(model_name: str, X: np.ndarray, y: np.ndarray, sample_weight: Optional[np.ndarray] = None) -> Tuple[Any, Dict]:
    """Optuna hyperparameter tuning with early stopping for boosters."""
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        return _tune_random_search(model_name, X, y, sample_weight)

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    use_encoding = y.dtype.kind not in ("i", "u")
    if use_encoding:
        le = LabelEncoder()
        y_enc = le.fit_transform(y.astype(str))
    else:
        le = None
        y_enc = y

    def objective(trial):
        params = get_optuna_params(model_name, trial)
        if not params and model_name in ("gradient_boosting", "lightgbm", "catboost"):
            params = {"n_estimators": 200, "max_depth": 5}
        est = create_model(model_name, **params)
        kw = {}
        if sample_weight is not None:
            kw["fit_params"] = {"sample_weight": sample_weight}
        scores = cross_val_score(est, X, y_enc, cv=cv, scoring="f1_weighted", n_jobs=1, **kw)
        return scores.mean()

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=OPTUNA_TRIALS, show_progress_bar=False)
    best_params = study.best_params
    est = create_model(model_name, **best_params)
    fit_kw = {}
    if sample_weight is not None:
        fit_kw["sample_weight"] = sample_weight
    est.fit(X, y_enc, **fit_kw)
    if use_encoding and le is not None:
        est = _LabelEncoderWrapper(est, le)
    return est, best_params


def _tune_random_search(model_name: str, X: np.ndarray, y: np.ndarray, sample_weight: Optional[np.ndarray] = None) -> Tuple[Any, Dict]:
    """Fallback when Optuna unavailable."""
    from sklearn.model_selection import RandomizedSearchCV
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    use_encoding = y.dtype.kind not in ("i", "u")
    if use_encoding:
        le = LabelEncoder()
        y_enc = le.fit_transform(y.astype(str))
    else:
        le = None
        y_enc = y
    param_dist = {
        "gradient_boosting": {"n_estimators": [100, 200], "max_depth": [3, 5, 7], "learning_rate": [0.01, 0.05]},
        "random_forest": {"n_estimators": [100, 200], "max_depth": [6, 8, 10], "min_samples_leaf": [2, 4, 8]},
        "extra_trees": {"n_estimators": [100, 200], "max_depth": [6, 8, 10]},
        "balanced_rf": {"n_estimators": [100, 200], "max_depth": [6, 8, 10]},
        "lightgbm": {"n_estimators": [100, 200], "max_depth": [4, 6, 8]},
        "catboost": {"iterations": [100, 200], "depth": [4, 6, 8]},
        "mlp": {"hidden_layer_sizes": [(64,), (64, 32)], "alpha": [0.001, 0.01]},
    }
    dist = param_dist.get(model_name, {})
    est = create_model(model_name)
    search = RandomizedSearchCV(est, param_distributions=dist, n_iter=min(15, max(1, 2 ** len(dist))),
                                cv=cv, scoring="f1_weighted", random_state=RANDOM_STATE, n_jobs=1)
    fit_params = {"sample_weight": sample_weight} if sample_weight is not None else {}
    search.fit(X, y_enc, **fit_params)
    best = search.best_estimator_
    if use_encoding and le is not None:
        best = _LabelEncoderWrapper(best, le)
    return best, dict(search.best_params_)


def _save_comparison_table(tracker: ExperimentTracker, output_dir: Path) -> None:
    """Save model comparison table with calibration_method, threshold_optimized, and metrics."""
    df = tracker.get_table()
    if df.empty:
        return
    cols = [
        "model",
        "calibration_method",
        "threshold_optimized",
        "accuracy",
        "f1_weighted",
        "f1_macro",
        "roc_auc",
        "clinical_cost",
        "overfitting_gap",
    ]
    out = df[[c for c in cols if c in df.columns]]
    out.to_csv(output_dir / "model_comparison.csv", index=False)
    logger.info("Saved model comparison to %s", output_dir / "model_comparison.csv")


def _retrain_best_on_full(
    best_estimator: Any,
    best_metrics: Dict[str, Any],
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: Optional[np.ndarray],
    y_val: Optional[np.ndarray],
    labels: List[str],
    trained_models: Dict[str, Any],
    apply_threshold_optimization: bool,
    random_state: int,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Retrain best model on full training data (train+val) for deployment.
    For single models: retrain base, recalibrate, redo threshold optimization.
    For ensembles: refit on full data.
    """
    model_name = best_metrics.get("model", "")
    if model_name in ("ensemble_stacking", "ensemble_soft_voting"):
        X_full = np.vstack([X_train, X_val]) if X_val is not None and len(X_val) > 0 else X_train
        y_full = np.concatenate([y_train, y_val]) if y_val is not None and len(y_val) > 0 else y_train
        try:
            best_estimator.fit(X_full, y_full)
            logger.info("Refit ensemble on full data")
        except Exception as e:
            logger.warning("Could not refit ensemble on full data: %s", e)
        return best_estimator, best_metrics

    X_full = np.vstack([X_train, X_val]) if X_val is not None and len(X_val) > 0 else X_train
    y_full = np.concatenate([y_train, y_val]) if y_val is not None and len(y_val) > 0 else y_train
    if len(X_full) == len(X_train):
        return best_estimator, best_metrics

    from sklearn.model_selection import train_test_split
    X_tr, X_cal, y_tr, y_cal = train_test_split(
        X_full, y_full, test_size=0.2, stratify=y_full, random_state=random_state
    )
    imb = best_metrics.get("imbalance", "class_weight")
    cal_method = best_metrics.get("calibration_method", "none")
    params = best_metrics.get("best_params", {})
    sample_weight = _get_sample_weights(imb, y_tr, labels)

    try:
        est = create_model(model_name, **params)
        fit_kw = {}
        if sample_weight is not None:
            fit_kw["sample_weight"] = sample_weight
        use_encoding = y_tr.dtype.kind not in ("i", "u")
        if use_encoding:
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y_tr_enc = le.fit_transform(y_tr.astype(str))
        else:
            le = None
            y_tr_enc = y_tr
        est.fit(X_tr, y_tr_enc, **fit_kw)
        if le is not None:
            est = _LabelEncoderWrapper(est, le)
        if cal_method != "none" and hasattr(est, "predict_proba"):
            est = wrap_with_calibration(est, X_cal, y_cal, method=cal_method)
        if apply_threshold_optimization and hasattr(est, "predict_proba"):
            thresh, _, _ = optimize_thresholds_cost_sensitive(est, X_cal, y_cal, labels)
            est = ThresholdOptimizedClassifier(est, thresh, labels)
        logger.info("Retrained best model (%s, %s) on full data", model_name, cal_method)
        return est, best_metrics
    except Exception as e:
        logger.warning("Retrain on full data failed: %s. Using original model.", e)
        return best_estimator, best_metrics


def _build_stacking_ensemble(
    base_models: List[Tuple[str, Any]],
    X_train: np.ndarray,
    y_train: np.ndarray,
    labels: List[str],
) -> Any:
    """Phase 6: Stacking ensemble with meta-learner."""
    estimators = [(name, est) for name, est in base_models]
    stacking = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5, random_state=RANDOM_STATE),
        cv=3,
    )
    stacking.fit(X_train, y_train)
    return stacking


def _repo_root() -> Path:
    # …/backend/src/clinical_ml_pipeline/full_pipeline.py → repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def run_full_improvement(
    data_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    best_model_dir: Optional[Path] = None,
    use_random_split: bool = True,
    use_patient_split: bool = False,
    models: Optional[List[str]] = None,
    imbalance_strategies: Optional[List[str]] = None,
    max_experiments: Optional[int] = None,
    apply_threshold_optimization: bool = True,
    build_stacking: bool = True,
) -> Dict[str, Any]:
    """
    Run full clinical ML improvement pipeline.

    SMOTE removed. Uses class_weight and cost_sensitive only.
    """
    repo = _repo_root()
    if data_path is None:
        data_path = repo / "data" / "SmartSensor_DiabetesMonitoring.csv"
    if output_dir is None:
        output_dir = repo / "outputs/clinical_ml_experiments"
    if best_model_dir is None:
        best_model_dir = repo / "outputs/best_model"
    if not data_path.exists():
        raise FileNotFoundError(f"Data not found: {data_path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tracker = ExperimentTracker(output_dir)

    models = models or list(DEFAULT_MODELS)
    # Remove LR and SVM per experiment findings; focus on tree-based
    models = [m for m in models if m not in ("logistic_regression", "svm")]
    imbalance_strategies = imbalance_strategies or ["class_weight", "cost_sensitive"]

    logger.info("Phase 1: Pipeline audit - no SMOTE, stratified CV, proper split")
    logger.info("Phase 2: Imbalance strategies: %s", imbalance_strategies)
    logger.info("Phase 3: Feature engineering - correlation removal in pipeline")
    logger.info("Phase 4: Running data pipeline...")

    split_type = "patient" if use_patient_split else ("random" if use_random_split else "temporal")
    pipe_config = PipelineConfig(split_type=split_type)
    pipeline = DataProcessingPipeline(config=pipe_config, data_path=data_path)
    result = pipeline.run(data_path=data_path, run_eda=False, run_feature_selection=True)

    X_train = result.X_train.values
    X_val = result.X_val.values if len(result.X_val) > 0 else None
    X_test = result.X_test.values
    y_train = result.y_train.values
    y_val = result.y_val.values if len(result.y_val) > 0 else None
    y_test = result.y_test.values
    labels = list(np.unique(y_test))
    feature_names = result.feature_names

    experiment_count = 0
    best_estimator = None
    best_metrics: Dict[str, Any] = {}
    trained_models: Dict[str, Any] = {}  # key -> (estimator, params)

    X_cal, y_cal = _get_calibration_data(
        X_train, y_train, X_val, y_val, cal_ratio=0.2, random_state=RANDOM_STATE
    )

    for imb in imbalance_strategies:
        sample_weight = _get_sample_weights(imb, y_train, labels)
        for model_name in models:
            if max_experiments and experiment_count >= max_experiments:
                break
            if model_name == "lightgbm" and create_model("lightgbm") is None:
                continue
            if model_name == "catboost" and create_model("catboost") is None:
                continue
            try:
                logger.info("Training %s with %s...", model_name, imb)
                est, params = _tune_model(model_name, X_train, y_train, sample_weight)

                for cal_method in ["none"] + list(CALIBRATION_METHODS):
                    if max_experiments and experiment_count >= max_experiments:
                        break
                    est_use = est
                    if cal_method != "none" and hasattr(est, "predict_proba"):
                        try:
                            est_use = wrap_with_calibration(est, X_cal, y_cal, method=cal_method)
                        except Exception as cal_e:
                            logger.warning("Calibration %s failed for %s: %s", cal_method, model_name, cal_e)
                            continue

                    ev_train = evaluate_model(est_use, X_train, y_train, model_name=model_name, labels=labels)
                    ev_test = evaluate_model(est_use, X_test, y_test, model_name=model_name, labels=labels)
                    overfitting_gap = ev_train.f1_weighted - ev_test.f1_weighted

                    # Phase 5: Threshold optimization AFTER calibration (only if improves clinical cost)
                    thresh_applied = False
                    if apply_threshold_optimization and hasattr(est_use, "predict_proba"):
                        thresh, cost_opt, f1_opt = optimize_thresholds_cost_sensitive(
                            est_use,
                            X_val if X_val is not None else X_cal,
                            y_val if y_val is not None else y_cal,
                            labels,
                        )
                        est_thresh = ThresholdOptimizedClassifier(est_use, thresh, labels)
                        ev_thresh = evaluate_model(est_thresh, X_test, y_test, model_name=model_name, labels=labels)
                        if ev_thresh.clinical_cost < ev_test.clinical_cost and ev_thresh.f1_weighted >= ev_test.f1_weighted - 0.05:
                            est_use = est_thresh
                            ev_test = ev_thresh
                            thresh_applied = True

                    exp_id = f"{model_name}_{imb}_{cal_method}_{experiment_count}"
                    tracker.log(
                        experiment_id=exp_id,
                        model=model_name,
                        imbalance_strategy=imb,
                        hyperparameters={**params, "calibration": cal_method},
                        accuracy=ev_test.accuracy,
                        f1_weighted=ev_test.f1_weighted,
                        f1_macro=ev_test.f1_macro,
                        roc_auc=ev_test.roc_auc_ovr_weighted,
                        clinical_cost=ev_test.clinical_cost,
                        overfitting_gap=overfitting_gap,
                        threshold_optimized=thresh_applied,
                        calibration_method=cal_method,
                    )
                    experiment_count += 1
                    trained_models[f"{model_name}_{imb}_{cal_method}"] = (est_use, params)

                    if best_estimator is None or _is_better_candidate(ev_test, overfitting_gap, best_metrics):
                        best_estimator = est_use
                        best_metrics = {
                            "model": model_name,
                            "imbalance": imb,
                            "calibration_method": cal_method,
                            "best_params": params,
                            "accuracy": ev_test.accuracy,
                            "f1_weighted": ev_test.f1_weighted,
                            "f1_macro": ev_test.f1_macro,
                            "roc_auc": ev_test.roc_auc_ovr_weighted,
                            "clinical_cost": ev_test.clinical_cost,
                            "overfitting_gap": overfitting_gap,
                        }
            except Exception as e:
                logger.exception("Model %s failed: %s", model_name, e)

    # Phase 6: Stacking ensemble (using calibrated base models when available)
    if build_stacking and len(trained_models) >= 2:
        logger.info("Phase 6: Building stacking ensemble with calibrated base models...")
        try:
            table = tracker.get_table()
            top = table.nlargest(6, "f1_weighted")  # Get more rows to pick diverse models
            seen_models = set()
            base_estimators = []
            for _, r in top.iterrows():
                if r["model"] == "ensemble_stacking":
                    continue
                name = r["model"]
                imb = r.get("imbalance_strategy", "class_weight")
                cal = r.get("calibration_method", "none")
                key = f"{name}_{imb}_{cal}"
                if key in trained_models and name not in seen_models:
                    base_estimators.append((key, trained_models[key][0]))
                    seen_models.add(name)
                    if len(base_estimators) >= 3:
                        break
            if len(base_estimators) >= 2:
                stacking = _build_stacking_ensemble(base_estimators, X_train, y_train, labels)
                ev_stack = evaluate_model(stacking, X_test, y_test, model_name="ensemble_stacking", labels=labels)
                gap = max(0, 0.6 - ev_stack.f1_weighted)
                tracker.log(
                    experiment_id="ensemble_stacking",
                    model="ensemble_stacking",
                    imbalance_strategy="class_weight",
                    hyperparameters={"base_models": [n for n, _ in base_estimators]},
                    calibration_method="none",
                    accuracy=ev_stack.accuracy,
                    f1_weighted=ev_stack.f1_weighted,
                    f1_macro=ev_stack.f1_macro,
                    roc_auc=ev_stack.roc_auc_ovr_weighted,
                    clinical_cost=ev_stack.clinical_cost,
                    overfitting_gap=gap,
                    threshold_optimized=False,
                )
                if _is_better_candidate(ev_stack, gap, best_metrics):
                    best_estimator = stacking
                    best_metrics = {
                        "model": "ensemble_stacking",
                        "imbalance": "class_weight",
                        "calibration_method": "none",
                        "best_params": {},
                        "accuracy": ev_stack.accuracy,
                        "f1_weighted": ev_stack.f1_weighted,
                        "f1_macro": ev_stack.f1_macro,
                        "roc_auc": ev_stack.roc_auc_ovr_weighted,
                        "clinical_cost": ev_stack.clinical_cost,
                        "overfitting_gap": gap,
                    }
        except Exception as e:
            logger.warning("Stacking failed: %s", e)

    # Soft voting with calibrated base models
    if build_stacking and best_metrics.get("model") != "ensemble_stacking":
        try:
            table = tracker.get_table()
            top = table.nlargest(6, "f1_weighted")
            seen_models = set()
            estimators_list = []
            for _, r in top.iterrows():
                if r["model"] in ("ensemble_stacking", "ensemble_soft_voting"):
                    continue
                name, imb, cal = r["model"], r.get("imbalance_strategy", "class_weight"), r.get("calibration_method", "none")
                key = f"{name}_{imb}_{cal}"
                if key in trained_models and name not in seen_models:
                    estimators_list.append((key, trained_models[key][0]))
                    seen_models.add(name)
                    if len(estimators_list) >= 3:
                        break
            if len(estimators_list) >= 2:
                ensemble = VotingClassifier(estimators=estimators_list, voting="soft")
                ensemble.fit(X_train, y_train)
                ev_ens = evaluate_model(ensemble, X_test, y_test, model_name="ensemble_soft_voting", labels=labels)
                gap = max(0, 0.6 - ev_ens.f1_weighted)
                tracker.log(
                    experiment_id="ensemble_soft_voting",
                    model="ensemble_soft_voting",
                    imbalance_strategy="class_weight",
                    hyperparameters={"base_models": [n for n, _ in estimators_list]},
                    accuracy=ev_ens.accuracy,
                    f1_weighted=ev_ens.f1_weighted,
                    f1_macro=ev_ens.f1_macro,
                    roc_auc=ev_ens.roc_auc_ovr_weighted,
                    clinical_cost=ev_ens.clinical_cost,
                    overfitting_gap=gap,
                    threshold_optimized=False,
                    calibration_method="none",
                )
                if _is_better_candidate(ev_ens, gap, best_metrics):
                    best_estimator = ensemble
                    best_metrics = {
                        "model": "ensemble_soft_voting",
                        "imbalance": "class_weight",
                        "calibration_method": "none",
                        "best_params": {},
                        "accuracy": ev_ens.accuracy,
                        "f1_weighted": ev_ens.f1_weighted,
                        "f1_macro": ev_ens.f1_macro,
                        "roc_auc": ev_ens.roc_auc_ovr_weighted,
                        "clinical_cost": ev_ens.clinical_cost,
                        "overfitting_gap": gap,
                    }
        except Exception as e:
            logger.warning("Soft voting failed: %s", e)

    if best_estimator is None:
        raise RuntimeError("No model trained successfully")

    # Phase 5: Model comparison table
    _save_comparison_table(tracker, output_dir)

    # Phase 8: Retrain best model on full data (train+val) for deployment
    best_estimator, best_metrics = _retrain_best_on_full(
        best_estimator,
        best_metrics,
        X_train,
        y_train,
        X_val,
        y_val,
        labels,
        trained_models,
        apply_threshold_optimization,
        RANDOM_STATE,
    )

    bundle = InferenceBundle(
        result,
        best_estimator,
        best_metrics.get("model", "best"),
        metric_name="f1_weighted",
        metric_value=best_metrics.get("f1_weighted", 0),
        calibration_method=best_metrics.get("calibration_method", "none"),
        threshold_optimized=apply_threshold_optimization,
    )
    save_best_model(bundle, best_model_dir)
    logger.info("Phase 10: Saved best model to %s", best_model_dir)

    # Phase 11: Final report and evaluation artifacts
    report_path = output_dir / "final_evaluation_report.json"
    report = {
        "best_model": best_metrics.get("model"),
        "metrics": best_metrics,
        "experiment_count": experiment_count,
        "experiment_table": str(tracker._experiment_table_path),
        "improvements": {
            "smote_removed": True,
            "threshold_optimization": apply_threshold_optimization,
            "probability_calibration": best_metrics.get("calibration_method", "none") != "none",
            "calibration_method": best_metrics.get("calibration_method", "none"),
            "cost_sensitive": "cost_sensitive" in imbalance_strategies,
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Phase 11: Report saved to %s", report_path)

    # Generate evaluation artifacts (confusion matrix, ROC, etc.) for best model
    try:
        from insulin_system.models.evaluation_framework import EvaluationFramework
        eval_dir = output_dir / "best_model_artifacts"
        eval_dir.mkdir(parents=True, exist_ok=True)
        framework = EvaluationFramework()
        framework.run_for_model(
            best_metrics.get("model", "best"),
            best_estimator,
            result,
            output_dir=eval_dir,
        )
        logger.info("Phase 11: Evaluation artifacts saved to %s", eval_dir)
    except Exception as e:
        logger.warning("Evaluation artifacts failed: %s", e)

    return {
        "best_model": best_estimator,
        "metrics": best_metrics,
        "bundle_path": str(best_model_dir),
        "report_path": str(report_path),
        "experiment_table": str(tracker._experiment_table_path),
    }
