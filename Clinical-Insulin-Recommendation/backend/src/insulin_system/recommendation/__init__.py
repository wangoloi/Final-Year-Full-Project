"""
Recommendation system (Step 6): prediction engine, clinical recommendations, explanations.
"""

from .recommendation_generator import (
    ClinicalRecommendation,
    DosageSuggestion,
    RecommendationGenerator,
)
from .explanation_generator import ExplanationOutput, RecommendationExplanationGenerator

__all__ = [
    "RecommendationGenerator",
    "ClinicalRecommendation",
    "DosageSuggestion",
    "RecommendationExplanationGenerator",
    "ExplanationOutput",
]
