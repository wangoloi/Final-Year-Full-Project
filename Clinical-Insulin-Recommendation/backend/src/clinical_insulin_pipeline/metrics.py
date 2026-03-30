"""Compatibility shim for ``from clinical_insulin_pipeline.metrics import ...``."""
from .evaluation.metrics import metrics_to_row, regression_metrics

__all__ = ["metrics_to_row", "regression_metrics"]
