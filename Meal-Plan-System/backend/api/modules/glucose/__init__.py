"""Glucose module - blood glucose tracking.
Microservice: single responsibility for glucose CRUD.
"""
from api.modules.glucose.router import router

__all__ = ["router"]
