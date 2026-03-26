"""LSTM sequence model (optional TensorFlow). Patient-level windows, no cross-patient leakage."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from smart_sensor_ml import config
from smart_sensor_ml.preprocess import PreprocessPipeline, _add_time_features, build_insulin_tier_labels

logger = logging.getLogger(__name__)

try:
    import tensorflow as tf

    tf.random.set_seed(config.RANDOM_STATE)
    _HAS_TF = True
except ImportError:
    _HAS_TF = False


def sequences_from_patients(
    df: pd.DataFrame,
    preprocessor: PreprocessPipeline,
    seq_len: int = 24,
    bin_edges: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build (n_samples, seq_len, n_features) and y (class per end-of-window row).
    groups: patient id string per sample (for splitting).
    """
    df = df.copy()
    _tcol = config.COL_MEASUREMENT_TIME if config.COL_MEASUREMENT_TIME in df.columns else config.COL_TIME
    df = df.sort_values([config.COL_PATIENT, _tcol])
    y_all, _ = build_insulin_tier_labels(df[config.COL_TARGET], bin_edges=bin_edges)

    X_list: List[np.ndarray] = []
    y_list: List[int] = []
    g_list: List[str] = []

    feat_names = preprocessor.selected_features
    # Precompute full transformed matrix row-aligned with df
    X_mat = preprocessor.transform(df)
    X_df = pd.DataFrame(X_mat, columns=feat_names, index=df.index)

    for pid, idx in df.groupby(config.COL_PATIENT).groups.items():
        _tcol = config.COL_MEASUREMENT_TIME if config.COL_MEASUREMENT_TIME in df.columns else config.COL_TIME
        order = df.loc[idx].sort_values(_tcol).index.tolist()
        if len(order) <= seq_len:
            continue
        arr = X_df.loc[order].values
        y_sub = y_all.loc[order].values
        for i in range(seq_len, len(order)):
            X_list.append(arr[i - seq_len : i])
            y_list.append(int(y_sub[i]))
            g_list.append(str(pid))

    if not X_list:
        raise ValueError("No sequences built — increase data or reduce seq_len.")
    X_seq = np.stack(X_list, axis=0).astype(np.float32)
    y_seq = np.asarray(y_list, dtype=np.int32)
    groups = np.asarray(g_list)
    return X_seq, y_seq, groups


def train_lstm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_features: int,
    epochs: int = 25,
    batch_size: int = 64,
) -> Any:
    if not _HAS_TF:
        raise RuntimeError("TensorFlow is not installed; install tensorflow to train LSTM.")
    from tensorflow import keras
    from tensorflow.keras import layers

    n_classes = config.N_CLASSES
    model = keras.Sequential(
        [
            layers.Input(shape=(X_train.shape[1], n_features)),
            layers.LSTM(48, return_sequences=False),
            layers.Dropout(0.25),
            layers.Dense(24, activation="relu"),
            layers.Dense(n_classes, activation="softmax"),
        ]
    )
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    y_train = np.clip(y_train, 0, n_classes - 1)
    model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        verbose=0,
        validation_split=0.1,
    )
    return model


def evaluate_lstm(model: Any, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
    y_test = np.clip(y_test, 0, config.N_CLASSES - 1)
    proba = model.predict(X_test, verbose=0)
    y_pred = np.argmax(proba, axis=1)
    acc = accuracy_score(y_test, y_pred)
    f1w = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    try:
        roc = roc_auc_score(y_test, proba, multi_class="ovr", average="weighted")
    except Exception:
        roc = float("nan")
    return {"accuracy": float(acc), "f1_weighted": float(f1w), "roc_auc_ovr": float(roc)}


def run_lstm_benchmark(
    df: pd.DataFrame,
    preprocessor: PreprocessPipeline,
    test_size: float = 0.2,
    random_state: int = 42,
    seq_len: int = 24,
    epochs: int = 20,
) -> Optional[Dict[str, Any]]:
    """
    Group split by patient on sequences; train LSTM; return metrics + model or None if TF missing.
    """
    if not _HAS_TF:
        logger.warning("Skipping LSTM: TensorFlow not installed.")
        return None
    try:
        X, y, groups = sequences_from_patients(
            df, preprocessor, seq_len=seq_len, bin_edges=preprocessor.insulin_bin_edges
        )
    except ValueError as e:
        logger.warning("LSTM skipped: %s", e)
        return None

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups))
    X_tr, X_te = X[train_idx], X[test_idx]
    y_tr, y_te = y[train_idx], y[test_idx]

    model = train_lstm(X_tr, y_tr, n_features=X.shape[2], epochs=epochs)
    metrics = evaluate_lstm(model, X_te, y_te)
    return {"model": model, "metrics": metrics, "n_train_seq": len(train_idx), "n_test_seq": len(test_idx)}
