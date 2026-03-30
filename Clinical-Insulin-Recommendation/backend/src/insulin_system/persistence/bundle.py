"""
Load clinical insulin regression bundle (joblib) for FastAPI inference.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BUNDLE_FILENAME = "inference_bundle.joblib"
METADATA_FILENAME = "metadata.json"
VERSIONS_DIR = "versions"
DEFAULT_BEST_MODEL_DIR = Path("outputs/best_model")


@dataclass
class InferenceBundle:
    """Loaded clinical regression artifact (preprocessor + sklearn/xgboost model)."""

    data: Dict[str, Any]
    path: Path

    @property
    def feature_names(self) -> List[str]:
        return list(self.data.get("feature_names") or [])

    @property
    def model_name(self) -> str:
        return str(self.data.get("best_model_name") or "clinical_regression")


class NotebookInferenceBundle(InferenceBundle):
    """Alias for notebook-exported bundles (same layout)."""

    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_inference_bundle_path(
    model_dir: Optional[Path] = None,
) -> Path:
    """Prefer model_dir/inference_bundle.joblib; else env GLUCOSENSE_INFERENCE_BUNDLE; else pipeline latest."""
    import os

    if model_dir is not None:
        p = Path(model_dir) / BUNDLE_FILENAME
        if p.is_file():
            return p
    env = os.environ.get("GLUCOSENSE_INFERENCE_BUNDLE", "").strip()
    if env:
        return Path(env)
    root = _repo_root()
    p1 = root / "outputs" / "best_model" / BUNDLE_FILENAME
    if p1.is_file():
        return p1
    p2 = root / "outputs" / "clinical_insulin_pipeline" / "latest" / "insulin_regression_bundle.joblib"
    if p2.is_file():
        return p2
    return p1


def save_best_model(*args: Any, **kwargs: Any) -> Path:
    raise NotImplementedError("Use clinical_insulin_pipeline training CLI to produce bundles.")


def list_model_versions(model_dir: Optional[Path] = None) -> List[int]:
    return []


def load_best_model(
    model_dir: Optional[Path] = None,
    version: Optional[int] = None,
) -> InferenceBundle:
    if version is not None:
        raise FileNotFoundError("Versioned bundles are not implemented for clinical regression.")
    path = resolve_inference_bundle_path(model_dir)
    if not path.is_file():
        raise FileNotFoundError(
            f"No inference bundle at {path}. Train with: python run_clinical_insulin_pipeline.py "
            "(writes outputs/clinical_insulin_pipeline/latest/) or copy to outputs/best_model/inference_bundle.joblib."
        )
    import joblib

    raw = joblib.load(path)
    if not isinstance(raw, dict) or "preprocessor" not in raw or "model" not in raw:
        raise ValueError(f"Invalid bundle format at {path}: expected dict with preprocessor and model.")
    logger.info("Loaded clinical insulin bundle from %s", path)
    return InferenceBundle(data=raw, path=path)


def write_deploy_metadata(best_model_dir: Path, bundle_data: Dict[str, Any]) -> None:
    """Optional metadata.json for dashboards (model name, metrics)."""
    meta = {
        "model_name": bundle_data.get("best_model_name", bundle_data.get("model_name", "clinical_regression")),
        "model_type": "clinical_insulin_regression",
        "classes": ["Low", "Moderate", "High"],
        "target": bundle_data.get("target_name", "Insulin_Dose"),
        "test_metrics": bundle_data.get("test_metrics", {}),
        "feature_names": bundle_data.get("feature_names", []),
    }
    best_model_dir.mkdir(parents=True, exist_ok=True)
    with open(best_model_dir / METADATA_FILENAME, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
