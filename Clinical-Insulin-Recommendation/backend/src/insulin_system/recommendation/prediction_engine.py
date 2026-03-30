"""
Prediction engine — removed with ML training pipeline.

Use a new inference integration when you add models back.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from ..config.schema import DataSchema, RecommendationConfig

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Single or batch prediction output."""

    labels: np.ndarray
    probabilities: np.ndarray
    classes: np.ndarray
    confidence: np.ndarray
    entropy: np.ndarray


class PredictionEngine:
    """Placeholder: real-time inference was backed by load_best_model + InferenceBundle."""

    def __init__(
        self,
        config: Optional[RecommendationConfig] = None,
        bundle: Any = None,
        model_dir: Optional[Path] = None,
    ) -> None:
        raise RuntimeError(
            "PredictionEngine requires a trained model bundle; the legacy training pipeline was removed."
        )
