"""
RNN (LSTM) model for insulin dosage prediction.
Uses synthetic sequences from cross-sectional data: reshape (n, features) -> (n, 1, features).
Falls back to MLP if TensorFlow/PyTorch unavailable.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

SEQ_FEATURES = ["glucose_level", "HbA1c", "BMI", "physical_activity", "insulin_sensitivity"]
RNN_EPOCHS = 15
RNN_BATCH_SIZE = 64
RANDOM_STATE = 42


def _reshape_for_rnn(X: np.ndarray, feature_names: List[str]) -> Tuple[np.ndarray, List[str]]:
    """Select sequence features and reshape to (n, 1, n_features)."""
    arr = np.asarray(X, dtype=np.float64)
    cols = list(feature_names) if feature_names else list(range(arr.shape[1]))
    if len(cols) != arr.shape[1]:
        cols = list(range(arr.shape[1]))
    seq_cols = [c for c in SEQ_FEATURES if c in cols]
    if len(seq_cols) < 2:
        seq_cols = cols[: min(5, len(cols))]
    idx = [cols.index(c) for c in seq_cols if c in cols]
    if not idx:
        idx = list(range(min(5, arr.shape[1])))
    X_seq = arr[:, idx]
    X_3d = X_seq.reshape(X_seq.shape[0], 1, X_seq.shape[1])
    return X_3d, [cols[i] for i in idx]


def _get_rnn_wrapper(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: List[str],
) -> Optional[Any]:
    """Build and train RNN (LSTM). Returns sklearn-compatible wrapper or None if failed."""
    from sklearn.preprocessing import LabelEncoder

    X_seq, _ = _reshape_for_rnn(X_train, feature_names)
    le = LabelEncoder()
    y_enc = le.fit_transform(np.asarray(y_train).astype(str))

    try:
        import tensorflow as tf
        from tensorflow.keras.layers import Dense, Dropout, LSTM
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.utils import to_categorical

        tf.random.set_seed(RANDOM_STATE)
        n_classes = len(le.classes_)
        n_features = X_seq.shape[2]
        model = Sequential([
            LSTM(32, input_shape=(1, n_features), return_sequences=False),
            Dropout(0.3),
            Dense(16, activation="relu"),
            Dense(n_classes, activation="softmax"),
        ])
        model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
        y_cat = to_categorical(y_enc, n_classes)
        model.fit(X_seq, y_cat, epochs=RNN_EPOCHS, batch_size=RNN_BATCH_SIZE, validation_split=0.1, verbose=0)

        class _TFWrapper:
            def __init__(self, m, label_enc, fnames):
                self._model = m
                self._le = label_enc
                self._feature_names = fnames
                self.classes_ = np.array(label_enc.classes_)

            def predict(self, X: np.ndarray) -> np.ndarray:
                X_3d, _ = _reshape_for_rnn(X, self._feature_names)
                probs = self._model.predict(np.asarray(X_3d), verbose=0)
                preds = probs.argmax(axis=1)
                return self._le.inverse_transform(preds)

            def predict_proba(self, X: np.ndarray) -> np.ndarray:
                X_3d, _ = _reshape_for_rnn(X, self._feature_names)
                return self._model.predict(np.asarray(X_3d), verbose=0)

        logger.info("Trained RNN (TensorFlow LSTM)")
        return _TFWrapper(model, le, feature_names)


    except ImportError:
        pass

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        torch.manual_seed(RANDOM_STATE)
        n_classes = len(le.classes_)
        n_features = X_seq.shape[2]

        class LSTMClassifier(nn.Module):
            def __init__(self):
                super().__init__()
                self.lstm = nn.LSTM(n_features, 32, batch_first=True)
                self.dropout = nn.Dropout(0.3)
                self.fc1 = nn.Linear(32, 16)
                self.fc2 = nn.Linear(16, n_classes)

            def forward(self, x):
                _, (h, _) = self.lstm(x)
                out = self.dropout(h.squeeze(0))
                out = torch.relu(self.fc1(out))
                return self.fc2(out)

        model = LSTMClassifier()
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters())
        X_t = torch.FloatTensor(X_seq)
        y_t = torch.LongTensor(y_enc)
        loader = DataLoader(TensorDataset(X_t, y_t), batch_size=RNN_BATCH_SIZE, shuffle=True)
        model.train()
        for _ in range(RNN_EPOCHS):
            for bx, by in loader:
                optimizer.zero_grad()
                logits = model(bx)
                loss = criterion(logits, by)
                loss.backward()
                optimizer.step()
        model.eval()

        class _PyTorchWrapper:
            def __init__(self, m, label_enc, fnames):
                self._model = m
                self._le = label_enc
                self._feature_names = fnames
                self.classes_ = np.array(label_enc.classes_)

            def predict(self, X: np.ndarray) -> np.ndarray:
                X_3d, _ = _reshape_for_rnn(X, self._feature_names)
                with torch.no_grad():
                    logits = self._model(torch.FloatTensor(np.asarray(X_3d)))
                    preds = logits.argmax(dim=1).numpy()
                return self._le.inverse_transform(preds)

            def predict_proba(self, X: np.ndarray) -> np.ndarray:
                import torch.nn.functional as F
                X_3d, _ = _reshape_for_rnn(X, self._feature_names)
                with torch.no_grad():
                    logits = self._model(torch.FloatTensor(np.asarray(X_3d)))
                    probs = F.softmax(logits, dim=1).numpy()
                return probs

        logger.info("Trained RNN (PyTorch LSTM)")
        return _PyTorchWrapper(model, le, feature_names)


    except ImportError:
        pass

    from sklearn.neural_network import MLPClassifier

    X_2d = X_seq.reshape(X_seq.shape[0], -1)
    model = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        max_iter=200,
        random_state=RANDOM_STATE,
        early_stopping=True,
        validation_fraction=0.1,
    )
    model.fit(X_2d, y_enc)

    class _MLPWrapper:
        def __init__(self, m, label_enc, fnames):
            self._model = m
            self._le = label_enc
            self._feature_names = fnames
            self.classes_ = np.array(label_enc.classes_)

        def predict(self, X: np.ndarray) -> np.ndarray:
            X_3d, _ = _reshape_for_rnn(X, self._feature_names)
            X_2d = X_3d.reshape(X_3d.shape[0], -1)
            return self._le.inverse_transform(self._model.predict(X_2d))

        def predict_proba(self, X: np.ndarray) -> np.ndarray:
            X_3d, _ = _reshape_for_rnn(X, self._feature_names)
            X_2d = X_3d.reshape(X_3d.shape[0], -1)
            return self._model.predict_proba(X_2d)

    logger.info("Trained RNN (MLP fallback - no TensorFlow/PyTorch)")
    return _MLPWrapper(model, le, feature_names)
