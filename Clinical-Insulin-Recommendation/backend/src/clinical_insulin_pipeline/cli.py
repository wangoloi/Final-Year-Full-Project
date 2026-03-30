"""Compatibility shim: ``python -m clinical_insulin_pipeline.cli`` / scripts import ``main`` here."""
from .train.cli import main

__all__ = ["main"]
