"""Chatbot module - RAG nutrition assistant.
Microservice: single responsibility for nutrition Q&A.
"""
from api.modules.chatbot.router import router

__all__ = ["router"]
