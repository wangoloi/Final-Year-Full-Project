"""Compatibility shim for ``from clinical_insulin_pipeline.training import run_training``."""
from .train.runner import TrainingResult, run_training

__all__ = ["TrainingResult", "run_training"]
