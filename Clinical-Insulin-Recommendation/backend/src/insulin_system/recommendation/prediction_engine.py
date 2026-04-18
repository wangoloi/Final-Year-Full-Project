"""
Prediction engine: real-time patient data input, model inference, optional threshold optimization.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from ..config.schema import DataSchema, RecommendationConfig
from ..persistence import load_best_model, InferenceBundle

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Single or batch prediction output."""

    labels: np.ndarray
    probabilities: np.ndarray
    classes: np.ndarray
    confidence: np.ndarray
    entropy: np.ndarray


def _entropy(proba: np.ndarray) -> float:
    eps = 1e-10
    return float(-np.sum(proba * np.log(proba + eps)))


class PredictionEngine:
    """Real-time patient data input and model inference using the saved best model."""

    def __init__(
        self,
        config: Optional[RecommendationConfig] = None,
        bundle: Optional[InferenceBundle] = None,
        model_dir: Optional[Path] = None,
    ) -> None:
        self._cfg = config or RecommendationConfig()
        self._schema = DataSchema()
        if bundle is not None:
            self._bundle = bundle
        else:
            model_dir = Path(model_dir) if model_dir else self._cfg.best_model_dir
            self._bundle = load_best_model(model_dir)

    @property
    def bundle(self) -> InferenceBundle:
        return self._bundle

    def process_input(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> pd.DataFrame:
        """Validate and convert input to DataFrame with schema expected by the bundle."""
        if isinstance(data, dict):
            cols = (self._schema.PATIENT_ID, *self._schema.CATEGORICAL, *self._schema.NUMERIC)
            row = {c: data.get(c) for c in cols}
            return pd.DataFrame([row])
        if isinstance(data, pd.DataFrame):
            return data
        raise TypeError("data must be pandas DataFrame or dict")

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        apply_threshold: bool = False,
    ) -> PredictionResult:
        """Run model inference."""
        if isinstance(X, pd.DataFrame):
            X_trans = self._bundle.transform(X)
        else:
            X_trans = np.asarray(X)
        proba = self._bundle.predict_proba(X_trans)
        classes = self._bundle.classes_
        if apply_threshold and self._cfg.class_thresholds:
            labels = self._apply_class_thresholds(proba, classes)
        else:
            labels = self._bundle.predict(X_trans)
        confidence = np.array([float(proba[i, np.argmax(proba[i])]) for i in range(len(proba))])
        entropy_arr = np.array([_entropy(proba[i]) for i in range(len(proba))])
        return PredictionResult(
            labels=labels,
            probabilities=proba,
            classes=classes,
            confidence=confidence,
            entropy=entropy_arr,
        )

    def _apply_class_thresholds(self, proba: np.ndarray, classes: np.ndarray) -> np.ndarray:
        thresh = self._cfg.class_thresholds or {}
        out = []
        for i in range(len(proba)):
            idx = int(np.argmax(proba[i]))
            out.append(classes[idx])
        return np.array(out)

    def predict_single(
        self,
        data: Union[pd.DataFrame, Dict[str, Any]],
        apply_threshold: bool = False,
    ) -> tuple:
        """One patient -> (predicted_label, proba_vector, confidence, entropy)."""
        df = self.process_input(data)
        res = self.predict(df, apply_threshold=apply_threshold)
        return (
            res.labels[0],
            res.probabilities[0],
            float(res.confidence[0]),
            float(res.entropy[0]),
        )


def optimize_probability_threshold(
    bundle: InferenceBundle,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> Dict[str, float]:
    """
    Optional: find per-class probability thresholds on validation set.
    Returns dict class_name -> threshold for use as RecommendationConfig.class_thresholds.
    """
    from sklearn.metrics import f1_score
    proba = bundle.predict_proba(X_val)
    classes = bundle.classes_
    label_to_idx = {str(c): i for i, c in enumerate(classes)}
    y_idx = np.array([label_to_idx.get(str(y), 0) for y in y_val])
    best_thresholds: Dict[str, float] = {}
    for i, c in enumerate(classes):
        c_name = str(c)
        best_f1 = 0.0
        best_t = 0.5
        for t in np.linspace(0.2, 0.9, 15):
            pred_i = (proba[:, i] >= t).astype(int)
            if pred_i.sum() == 0:
                continue
            f1 = f1_score(y_idx == i, pred_i, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_t = t
        best_thresholds[c_name] = best_t
    return best_thresholds
