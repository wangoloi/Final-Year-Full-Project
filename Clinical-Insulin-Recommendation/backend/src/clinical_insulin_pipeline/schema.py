"""Compatibility shim for ``from clinical_insulin_pipeline.schema import ...``."""
from .serving.schema import InsulinPredictionInput, postprocess_dose

__all__ = ["InsulinPredictionInput", "postprocess_dose"]
