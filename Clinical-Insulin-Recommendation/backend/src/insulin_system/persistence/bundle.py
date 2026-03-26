"""
Inference bundle: full preprocessing + model for saving/loading and prediction.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ..config.schema import DataSchema
from ..data_processing.pipeline import PipelineResult

logger = logging.getLogger(__name__)

# Default path for the saved best model used by the system
DEFAULT_BEST_MODEL_DIR = Path("outputs/best_model")
BUNDLE_FILENAME = "inference_bundle.joblib"
METADATA_FILENAME = "metadata.json"
VERSIONS_DIR = "versions"
CURRENT_VERSION_FILE = "current_version.txt"


class InferenceBundle:
    """
    Fitted preprocessing pipeline + model for inference.
    Accepts raw DataFrames (same schema as training) and returns predictions.
    """

    def __init__(
        self,
        pipeline_result: PipelineResult,
        model: Any,
        model_name: str,
        metric_name: str = "f1_weighted",
        metric_value: float = 0.0,
        **extra_metadata: Any,
    ) -> None:
        self._schema = DataSchema()
        self._imputer = pipeline_result.imputer
        self._outlier_handler = pipeline_result.outlier_handler
        self._feature_engineer = pipeline_result.feature_engineer
        self._encoder = pipeline_result.encoder
        self._scaler = pipeline_result.scaler
        self._feature_selector = pipeline_result.feature_selector
        self._model = model
        self._feature_names = list(pipeline_result.feature_names)
        self._model_name = model_name
        self._metric_name = metric_name
        self._metric_value = float(metric_value)
        self._extra_metadata = dict(extra_metadata)
        self._classes_ = self._get_classes()

    def _get_classes(self) -> np.ndarray:
        est = self._model
        if hasattr(est, "named_steps") and "clf" in getattr(est, "named_steps", {}):
            est = est.named_steps["clf"]
        if hasattr(est, "classes_"):
            return np.asarray(est.classes_)
        return np.array([])

    @property
    def feature_names(self) -> List[str]:
        return list(self._feature_names)

    @property
    def classes_(self) -> np.ndarray:
        return self._classes_

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def metric_name(self) -> str:
        return self._metric_name

    @property
    def metric_value(self) -> float:
        return self._metric_value

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Run full preprocessing: impute -> outlier -> feature_engineer -> encode -> scale -> select.
        Returns feature matrix X (n_samples, n_features) for model input.
        """
        if self._imputer is None:
            raise RuntimeError("InferenceBundle not properly initialized (missing imputer)")
        # Coerce numeric columns to float so no str/float comparison anywhere in pipeline
        out = df.copy()
        numeric_cols = list(self._schema.NUMERIC) + list(getattr(self._schema, "CONTEXTUAL_IMPUTE", ()))
        for col in numeric_cols:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").astype(np.float64)
        # Ensure contextual columns exist (inference may omit them)
        for col, default in [("iob", 0.0), ("anticipated_carbs", 0.0), ("glucose_trend", "stable")]:
            if col not in out.columns:
                out[col] = default
        out = self._imputer.transform(out)
        # Re-coerce and fill NaN so outlier/scaler/model never see object or NaN
        for col in numeric_cols:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).astype(np.float64)
        if self._outlier_handler is not None:
            out = self._outlier_handler.transform(out)
        if self._feature_engineer is not None:
            out = self._feature_engineer.transform(out)
        out = self._encoder.transform(out)
        out = self._scaler.transform(out)
        exclude = {self._schema.PATIENT_ID, self._schema.TARGET, "_outlier_flag"}
        feat_cols = [c for c in out.columns if c not in exclude]
        X = out[feat_cols]
        if self._feature_selector is not None:
            X = self._feature_selector.transform(X)
        return np.asarray(X, dtype=np.float64)

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict class labels. X: raw DataFrame (schema as training) or already transformed array."""
        if isinstance(X, pd.DataFrame):
            X = self.transform(X)
        return self._model.predict(X)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict class probabilities. X: raw DataFrame or transformed array."""
        if isinstance(X, pd.DataFrame):
            X = self.transform(X)
        if hasattr(self._model, "predict_proba"):
            return np.asarray(self._model.predict_proba(X))
        return np.zeros((len(X), len(self._classes_)), dtype=np.float64)

    def to_metadata(self) -> Dict[str, Any]:
        meta = {
            "model_name": self._model_name,
            "metric_name": self._metric_name,
            "metric_value": self._metric_value,
            "n_features": len(self._feature_names),
            "feature_names": self._feature_names,
            "classes": self._classes_.tolist(),
        }
        extra = getattr(self, "_extra_metadata", {})
        meta.update(extra)
        return meta


class NotebookInferenceBundle(InferenceBundle):
    """
    Inference bundle built from notebook-style pipeline (LabelEncoder, MI features, StandardScaler).
    Implements the same interface as InferenceBundle for API compatibility.
    """

    def __init__(
        self,
        model: Any,
        scaler: StandardScaler,
        label_encoders: Dict[str, LabelEncoder],
        feature_names: List[str],
        model_name: str,
        metric_name: str = "f1_weighted",
        metric_value: float = 0.0,
    ) -> None:
        self._schema = DataSchema()
        self._model = model
        self._scaler = scaler
        self._label_encoders = label_encoders
        self._feature_names = list(feature_names)
        self._model_name = model_name
        self._metric_name = metric_name
        self._metric_value = float(metric_value)
        # Notebook uses LabelEncoder for target; model predicts integers
        target_enc = label_encoders.get(self._schema.TARGET)
        if target_enc is not None:
            self._classes_ = np.array(target_enc.classes_)
        else:
            self._classes_ = getattr(model, "classes_", np.array([]))
        # Pipeline components (not used; NotebookInferenceBundle overrides transform)
        self._imputer = None
        self._outlier_handler = None
        self._feature_engineer = None
        self._encoder = None
        self._feature_selector = None

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Encode categoricals -> select features -> fillna(0) -> scale (notebook logic)."""
        row = df.copy()
        for col, le in self._label_encoders.items():
            if col == self._schema.TARGET:
                continue
            if col in row.columns:
                vals = row[col].astype(str)
                # Handle unseen labels
                unseen = ~np.isin(vals, le.classes_)
                if unseen.any():
                    vals = vals.where(~unseen, le.classes_[0])
                row[col] = le.transform(vals)
        # Ensure we have selected features
        for f in self._feature_names:
            if f not in row.columns:
                row[f] = 0.0
        X = row[self._feature_names].fillna(0).astype(np.float64).values
        return self._scaler.transform(X)

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict and inverse-transform to string labels."""
        if isinstance(X, pd.DataFrame):
            X = self.transform(X)
        pred_int = self._model.predict(X)
        target_enc = self._label_encoders.get(self._schema.TARGET)
        if target_enc is not None:
            return target_enc.inverse_transform(pred_int)
        return pred_int

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict class probabilities."""
        if isinstance(X, pd.DataFrame):
            X = self.transform(X)
        if hasattr(self._model, "predict_proba"):
            return np.asarray(self._model.predict_proba(X))
        return np.zeros((len(X), len(self._classes_)), dtype=np.float64)


def _get_next_version(out_dir: Path) -> int:
    """Get next version number from versions subdir."""
    versions_dir = out_dir / VERSIONS_DIR
    if not versions_dir.exists():
        return 1
    existing = [f.stem.replace("v", "") for f in versions_dir.glob("v*") if f.is_dir()]
    nums = []
    for s in existing:
        try:
            nums.append(int(s))
        except ValueError:
            pass
    return max(nums, default=0) + 1


def save_best_model(
    bundle: InferenceBundle,
    output_dir: Optional[Path] = None,
    versioned: bool = True,
) -> Path:
    """
    Save the inference bundle (preprocessors + model) to disk.
    Writes inference_bundle.joblib and metadata.json.
    If versioned=True, also saves a copy under versions/vN/ for rollback.
    """
    try:
        import joblib
    except ImportError:
        raise ImportError("joblib is required for saving the model. Install with: pip install joblib")

    out_dir = Path(output_dir) if output_dir else DEFAULT_BEST_MODEL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save full bundle with joblib (model + preprocessors)
    bundle_path = out_dir / BUNDLE_FILENAME
    joblib.dump(bundle, bundle_path)
    logger.info("Saved inference bundle to %s", bundle_path)

    meta_path = out_dir / METADATA_FILENAME
    meta = bundle.to_metadata()
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved metadata to %s", meta_path)

    # Versioned copy for rollback
    if versioned:
        v = _get_next_version(out_dir)
        versions_dir = out_dir / VERSIONS_DIR
        version_dir = versions_dir / f"v{v}"
        version_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(bundle_path, version_dir / BUNDLE_FILENAME)
        shutil.copy2(meta_path, version_dir / METADATA_FILENAME)
        version_file = out_dir / CURRENT_VERSION_FILE
        version_file.write_text(str(v), encoding="utf-8")
        logger.info("Saved versioned copy to %s (v%d)", version_dir, v)

    return out_dir


def list_model_versions(model_dir: Optional[Path] = None) -> List[int]:
    """List available version numbers for rollback."""
    dir_path = Path(model_dir) if model_dir else DEFAULT_BEST_MODEL_DIR
    versions_dir = dir_path / VERSIONS_DIR
    if not versions_dir.exists():
        return []
    nums = []
    for f in versions_dir.glob("v*"):
        if f.is_dir():
            try:
                nums.append(int(f.stem.replace("v", "")))
            except ValueError:
                pass
    return sorted(nums, reverse=True)


def load_best_model(
    model_dir: Optional[Path] = None,
    version: Optional[int] = None,
) -> InferenceBundle:
    """
    Load the inference bundle from disk (default: outputs/best_model).
    If version is set, load from versions/v{version}/; else load from root.
    Returns InferenceBundle for predict / predict_proba / transform.
    Handles corrupted or truncated files with clear error messages.
    """
    try:
        import joblib
    except ImportError:
        raise ImportError("joblib is required for loading the model. Install with: pip install joblib")

    dir_path = Path(model_dir) if model_dir else DEFAULT_BEST_MODEL_DIR
    if version is not None:
        dir_path = dir_path / VERSIONS_DIR / f"v{version}"
    bundle_path = dir_path / BUNDLE_FILENAME
    if not bundle_path.exists():
        raise FileNotFoundError(
            f"No saved model found at {bundle_path}. "
            "Run evaluation first (e.g. python run_evaluation.py) to train and save the best model."
        )

    # Validate file size (corrupted/truncated bundles are often very small)
    file_size = bundle_path.stat().st_size
    if file_size < 1000:
        raise RuntimeError(
            f"Model file appears corrupted or truncated ({file_size} bytes). "
            "Re-run the pipeline: python run_pipeline.py"
        )

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*Trying to unpickle.*", category=UserWarning)
            bundle = joblib.load(bundle_path)
    except EOFError as e:
        logger.error("Model file corrupted or truncated (EOFError): %s", bundle_path)
        raise RuntimeError(
            "Model file is corrupted or incomplete. Re-run the pipeline to regenerate: python run_pipeline.py"
        ) from e
    except Exception as e:
        logger.exception("Failed to load model from %s", bundle_path)
        raise RuntimeError(
            f"Could not load model: {e}. Re-run the pipeline: python run_pipeline.py"
        ) from e

    if not isinstance(bundle, InferenceBundle):
        raise RuntimeError(
            f"Loaded object is not an InferenceBundle (got {type(bundle).__name__}). "
            "Re-run the pipeline: python run_pipeline.py"
        )

    logger.info("Loaded inference bundle from %s (model=%s)", bundle_path, getattr(bundle, "model_name", "?"))
    return bundle
