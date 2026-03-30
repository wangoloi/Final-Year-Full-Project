"""Compatibility shim for ``from clinical_insulin_pipeline.inference import predict_insulin_dose``."""
from .serving.predict import (
    load_bundle,
    predict_from_insulin_prediction_input,
    predict_insulin_dose,
    row_dict_from_input,
)

__all__ = [
    "load_bundle",
    "predict_from_insulin_prediction_input",
    "predict_insulin_dose",
    "row_dict_from_input",
]
