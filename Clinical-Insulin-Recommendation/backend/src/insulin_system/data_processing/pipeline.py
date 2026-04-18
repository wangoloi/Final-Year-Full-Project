from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class PipelineResult:
    """
    Lightweight container for fitted preprocessing steps.

    The training pipeline builds these objects; the inference bundle persists them
    together with the fitted estimator.
    """

    imputer: Any
    outlier_handler: Optional[Any] = None
    feature_engineer: Optional[Any] = None
    encoder: Optional[Any] = None
    scaler: Optional[Any] = None
    feature_selector: Optional[Any] = None
    feature_names: List[str] = field(default_factory=list)

