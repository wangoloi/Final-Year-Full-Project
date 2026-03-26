"""
Model Development Module: baseline and advanced classifiers with tuning and evaluation.
"""

from .definitions import get_model_definitions, MODEL_NAMES
from .training import ModelTrainer, TrainingResult
from .evaluation import evaluate_model, compare_models, EvaluationResult
from .evaluation_framework import EvaluationFramework, FullEvaluationArtifacts

__all__ = [
    "get_model_definitions",
    "MODEL_NAMES",
    "ModelTrainer",
    "TrainingResult",
    "evaluate_model",
    "compare_models",
    "EvaluationResult",
    "EvaluationFramework",
    "FullEvaluationArtifacts",
]
