"""Training entrypoints (CLI + run_training)."""
from .cli import main
from .runner import TrainingResult, run_training

__all__ = ["TrainingResult", "main", "run_training"]
