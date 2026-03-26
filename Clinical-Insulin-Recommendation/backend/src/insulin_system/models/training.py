"""
Model training with hyperparameter tuning, stratified CV, and class imbalance handling.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold
from sklearn.preprocessing import LabelEncoder

from ..config.schema import ModelConfig
from ..exceptions import DataValidationError
from .definitions import get_model_definitions

logger = logging.getLogger(__name__)


def _is_xgboost(estimator: Any) -> bool:
    """True if estimator is XGBClassifier (does not support class_weight)."""
    try:
        import xgboost as xgb
        return isinstance(estimator, xgb.XGBClassifier)
    except ImportError:
        return False


@dataclass
class TrainingResult:
    """Result of training a single model."""

    model_name: str
    best_estimator: Any
    best_params: Dict[str, Any]
    best_cv_score: float
    cv_results: Optional[Dict[str, Any]] = None
    classes_: Optional[np.ndarray] = None


def _make_estimator_with_imbalance(
    base_estimator: Any,
    imbalance_strategy: str,
    random_state: int,
    smote_k_neighbors: int = 5,
) -> Tuple[Any, bool]:
    """Wrap estimator in a Pipeline with optional SMOTE; return (estimator, is_pipeline)."""
    is_pipeline = False
    if imbalance_strategy == "smote":
        try:
            from imblearn.over_sampling import SMOTE
            from imblearn.pipeline import Pipeline as ImbPipeline
            smote = SMOTE(random_state=random_state, k_neighbors=min(smote_k_neighbors, 5))
            pipe = ImbPipeline([("smote", smote), ("clf", base_estimator)])
            return pipe, True
        except ImportError:
            logger.warning("imbalanced-learn not installed; falling back to class_weight")
            imbalance_strategy = "class_weight"
    if imbalance_strategy == "class_weight" and hasattr(base_estimator, "set_params"):
        if not _is_xgboost(base_estimator):
            try:
                base_estimator.set_params(class_weight="balanced")
            except Exception:
                pass
    return base_estimator, is_pipeline


def _compute_class_weights(
    y: np.ndarray,
    class_names: Optional[np.ndarray] = None,
    minority_classes: Optional[Tuple[str, ...]] = None,
    multiplier: float = 1.0,
) -> Tuple[np.ndarray, Dict[Any, float]]:
    """Compute per-class weights; optionally boost minority. Returns (sample_weights, class_weight_dict)."""
    classes, counts = np.unique(y, return_counts=True)
    n = len(y)
    n_classes = len(classes)
    weight_per_class = np.array(n / (n_classes * counts), dtype=np.float64)
    if multiplier != 1.0 and minority_classes:
        for i, c in enumerate(classes):
            label_str = (
                str(class_names[int(c)]) if class_names is not None and np.issubdtype(classes.dtype, np.integer)
                else str(c)
            )
            if label_str in minority_classes:
                weight_per_class[i] *= multiplier
    # Keys must match y dtype (int for encoded, str for raw labels)
    class_weight_dict = {c: float(w) for c, w in zip(classes, weight_per_class)}
    if np.issubdtype(classes.dtype, np.integer):
        class_weight_dict = {int(k): v for k, v in class_weight_dict.items()}
    sample_weights = weight_per_class[np.searchsorted(classes, y)]
    return sample_weights, class_weight_dict


def _get_sample_weights(
    y: np.ndarray,
    class_names: Optional[np.ndarray] = None,
    minority_classes: Optional[Tuple[str, ...]] = None,
    multiplier: float = 1.0,
) -> np.ndarray:
    """Compute balanced sample weights; optionally boost minority classes (for XGBoost etc.)."""
    sample_weights, _ = _compute_class_weights(y, class_names, minority_classes, multiplier)
    return sample_weights


def _wrap_calibrated(
    estimator: Any,
    X: np.ndarray,
    y: np.ndarray,
    config: Any,
) -> Any:
    """Wrap estimator in CalibratedClassifierCV for better probability estimates."""
    cv = getattr(config, "calibration_cv", 3)
    try:
        calibrated = CalibratedClassifierCV(
            estimator,
            method="isotonic",
            cv=min(cv, 3),
            ensemble=True,
        )
        calibrated.fit(X, y)
        return calibrated
    except Exception as e:
        logger.warning("Calibration failed (%s); using uncalibrated model", e)
        return estimator


def _needs_label_encoding(base_estimator: Any) -> bool:
    """True if the estimator expects integer labels (XGBoost, MLPClassifier, StackingClassifier with XGB)."""
    if _is_xgboost(base_estimator):
        return True
    from sklearn.neural_network import MLPClassifier
    from sklearn.ensemble import StackingClassifier
    if isinstance(base_estimator, MLPClassifier):
        return True
    if isinstance(base_estimator, StackingClassifier):
        for _, est in base_estimator.estimators:
            if _is_xgboost(est):
                return True
    return False


class _LabelEncoderWrapper:
    """Wraps an estimator so predict/predict_proba return original labels (inverse of LabelEncoder)."""

    def __init__(self, estimator: Any, label_encoder: LabelEncoder):
        self._estimator = estimator
        self._le = label_encoder
        self.classes_ = getattr(label_encoder, "classes_", None)

    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Sklearn-compatible: required for clone()."""
        return {"estimator": self._estimator, "label_encoder": self._le}

    def set_params(self, **params: Any) -> "_LabelEncoderWrapper":
        """Sklearn-compatible: required for clone(). Handles unfitted cloned encoders."""
        if "estimator" in params:
            self._estimator = params["estimator"]
        if "label_encoder" in params:
            self._le = params["label_encoder"]
            self.classes_ = getattr(self._le, "classes_", None)
        return self

    def predict(self, X: Any) -> np.ndarray:
        pred = self._estimator.predict(X)
        if pred.dtype.kind in ("i", "u") or np.issubdtype(pred.dtype, np.integer):
            return self._le.inverse_transform(pred.astype(int))
        return pred

    def predict_proba(self, X: Any) -> np.ndarray:
        return self._estimator.predict_proba(X)

    def fit(self, X: Any, y: Any, **kwargs: Any) -> "_LabelEncoderWrapper":
        y_arr = np.asarray(y).astype(str)
        # Use fit_transform so cloned (unfitted) encoders work in learning_curve/cross_val
        if getattr(self._le, "classes_", None) is None or len(getattr(self._le, "classes_", [])) == 0:
            y_enc = self._le.fit_transform(y_arr)
        else:
            y_enc = self._le.transform(y_arr)
        self.classes_ = np.array(self._le.classes_)
        self._estimator.fit(X, y_enc, **kwargs)
        return self


class ModelTrainer:
    """
    Trains a single model or all models with hyperparameter tuning,
    stratified CV, and optional SMOTE/class_weight for imbalance.
    """

    def __init__(
        self,
        config: Optional[ModelConfig] = None,
        exclude_mlp: bool = True,
        include_rnn: bool = True,
        include_stacking: bool = True,
    ):
        self._config = config or ModelConfig()
        self._definitions = get_model_definitions(
            exclude_mlp=exclude_mlp,
            include_rnn=include_rnn,
            include_stacking=include_stacking,
        )

    def train_single(
        self,
        model_name: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> TrainingResult:
        """
        Train one model with tuning. Uses stratified CV; optionally evaluate on val set.
        """
        if model_name not in self._definitions:
            raise DataValidationError(f"Unknown model: {model_name}")

        # RNN uses custom training path (no GridSearchCV)
        if model_name == "rnn_lstm":
            return self._train_rnn(X_train, y_train)

        base_est, param_grid = self._definitions[model_name]
        import sklearn.base
        estimator = sklearn.base.clone(base_est)
        estimator, is_pipeline = _make_estimator_with_imbalance(
            estimator,
            self._config.imbalance_strategy,
            self._config.random_state,
            self._config.smote_k_neighbors,
        )
        if is_pipeline:
            param_grid = {"clf__" + k: v for k, v in param_grid.items()}
        cv = StratifiedKFold(
            n_splits=self._config.cv_folds,
            shuffle=True,
            random_state=self._config.random_state,
        )
        if self._config.search_type == "random":
            search = RandomizedSearchCV(
                estimator,
                param_distributions=param_grid,
                n_iter=min(self._config.random_search_n_iter, self._total_combinations(param_grid)),
                cv=cv,
                scoring=self._config.scoring,
                n_jobs=self._config.n_jobs,
                random_state=self._config.random_state,
                refit=True,
            )
        else:
            search = GridSearchCV(
                estimator,
                param_grid=param_grid,
                cv=cv,
                scoring=self._config.scoring,
                n_jobs=self._config.n_jobs,
                refit=True,
            )
        # Convert to plain numpy so sklearn CV indexing works (pandas PyArrow-backed arrays fail with "only integer scalar arrays can be converted to a scalar index")
        if isinstance(X_train, np.ndarray):
            X = np.ascontiguousarray(X_train.astype(np.float64))
        else:
            X = np.ascontiguousarray(X_train.to_numpy(dtype=np.float64, copy=True))
        if isinstance(y_train, np.ndarray):
            y = np.asarray(y_train, copy=True).ravel()
        else:
            y = np.asarray(y_train.to_numpy(copy=True)).ravel()
        label_encoder = None
        # Safe check: need encoding for XGB/MLP when y is not integer (avoid np.issubdtype on pandas StringDtype)
        needs_encode = _needs_label_encoding(base_est) and y.dtype.kind not in ("i", "u")
        if needs_encode:
            label_encoder = LabelEncoder()
            y = label_encoder.fit_transform(y.astype(str))
        class_names = label_encoder.classes_ if label_encoder is not None else np.unique(y_train) if hasattr(y_train, "__iter__") else None
        if class_names is not None and hasattr(class_names, "__len__") and len(class_names) == 0:
            class_names = None
        mult = getattr(self._config, "minority_class_weight_multiplier", 1.0)
        minority = getattr(self._config, "minority_classes", ())
        # Cost-sensitive: custom class_weight for sklearn, sample_weight for XGBoost
        if self._config.imbalance_strategy == "class_weight" and mult != 1.0 and minority:
            sample_weights, class_weight_dict = _compute_class_weights(y, class_names, minority, mult)
            if not _is_xgboost(base_est):
                try:
                    param = "clf__class_weight" if is_pipeline else "class_weight"
                    estimator.set_params(**{param: class_weight_dict})
                except Exception:
                    pass
        fit_params = {}
        # Do NOT pass sample_weight when using SMOTE: pipeline oversamples (X,y) so sizes would mismatch
        try:
            if self._config.imbalance_strategy == "class_weight":
                if _is_xgboost(base_est):
                    sw = _get_sample_weights(y, class_names, minority if minority else None, mult)
                    fit_params["sample_weight"] = sw
                elif is_pipeline and _is_xgboost(base_est):
                    sw = _get_sample_weights(y, class_names, minority if minority else None, mult)
                    fit_params["clf__sample_weight"] = sw
        except Exception:
            pass
        if fit_params:
            search.fit(X, y, **fit_params)
        else:
            search.fit(X, y)
        best = search.best_estimator_
        if label_encoder is not None:
            best = _LabelEncoderWrapper(best, label_encoder)
        # Optional probability calibration (improves reliability of confidence scores)
        if getattr(self._config, "use_calibration", False):
            y_for_cal = (
                label_encoder.inverse_transform(y.astype(int))
                if label_encoder is not None
                else y
            )
            best = _wrap_calibrated(best, X, y_for_cal, self._config)
        if hasattr(best, "classes_"):
            classes_ = best.classes_
        elif hasattr(best, "named_steps") and "clf" in best.named_steps:
            classes_ = getattr(best.named_steps["clf"], "classes_", np.unique(y_train))
        else:
            classes_ = np.unique(y_train) if hasattr(y_train, "unique") else np.unique(y)
        return TrainingResult(
            model_name=model_name,
            best_estimator=best,
            best_params=search.best_params_,
            best_cv_score=float(search.best_score_),
            cv_results=search.cv_results_,
            classes_=classes_,
        )

    def _train_rnn(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> TrainingResult:
        """Train RNN/LSTM via custom path."""
        from .rnn import _get_rnn_wrapper

        X = np.ascontiguousarray(X_train.to_numpy(dtype=np.float64, copy=True))
        y = np.asarray(y_train.to_numpy(copy=True)).ravel()
        feature_names = list(X_train.columns) if hasattr(X_train, "columns") else []
        wrapper = _get_rnn_wrapper(X, y, feature_names)
        if wrapper is None:
            raise RuntimeError("RNN training failed (TensorFlow, PyTorch, and MLP fallback unavailable)")
        classes_ = np.array(wrapper.classes_)
        return TrainingResult(
            model_name="rnn_lstm",
            best_estimator=wrapper,
            best_params={},
            best_cv_score=0.0,
            cv_results=None,
            classes_=classes_,
        )

    def _total_combinations(self, param_grid: Dict[str, List[Any]]) -> int:
        n = 1
        for v in param_grid.values():
            n *= len(v)
        return n

    def train_all(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        model_names: Optional[List[str]] = None,
    ) -> List[TrainingResult]:
        """Train all (or selected) models and return list of TrainingResult."""
        names = model_names or list(self._definitions.keys())
        results = []
        for name in names:
            if name not in self._definitions:
                continue
            logger.info("Training model: %s", name)
            try:
                res = self.train_single(name, X_train, y_train, X_val, y_val)
                results.append(res)
            except Exception as e:
                logger.exception("Model %s failed: %s", name, e)
        return results
