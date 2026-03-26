"""
Recommendation system (Step 6): prediction engine, clinical recommendations, explanations.
"""

from .prediction_engine import PredictionEngine, PredictionResult
from .recommendation_generator import (
    ClinicalRecommendation,
    DosageSuggestion,
    RecommendationGenerator,
)
from .explanation_generator import ExplanationOutput, RecommendationExplanationGenerator

__all__ = [
    "PredictionEngine",
    "PredictionResult",
    "RecommendationGenerator",
    "ClinicalRecommendation",
    "DosageSuggestion",
    "RecommendationExplanationGenerator",
    "ExplanationOutput",
]
