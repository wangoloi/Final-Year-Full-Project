"""Auth module - register, login, JWT.
Microservice: single responsibility for authentication.
"""
from api.modules.auth.router import router

__all__ = ["router"]
