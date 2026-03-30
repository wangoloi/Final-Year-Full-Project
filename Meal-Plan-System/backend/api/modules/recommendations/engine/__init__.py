"""Hybrid recommendation engine: context → constraints → pools → scoring → optimization → explainability."""
from api.modules.recommendations.engine.pipeline import run_recommendation_pipeline

__all__ = ["run_recommendation_pipeline"]
