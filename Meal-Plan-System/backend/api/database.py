"""Database - re-export from shared (backward compatibility)."""
from api.shared.database import (
    engine,
    SessionLocal,
    Base,
    get_db,
    init_db,
)

__all__ = ["engine", "SessionLocal", "Base", "get_db", "init_db"]
