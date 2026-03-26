"""Recommendations module - personalized food suggestions.
Microservice: single responsibility for recommendations.
"""
from api.modules.recommendations.router import router

__all__ = ["router"]
