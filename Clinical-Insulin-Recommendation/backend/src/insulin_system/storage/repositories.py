"""
Data access layer: repository abstraction over persistence.

Exposes only data retrieval and storage. No business logic.
Routes and services depend on this layer instead of db directly for testability and clarity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import db


class RecordsRepository:
    """Persistence for prediction/recommendation records."""

    def insert(
        self,
        endpoint: str,
        request_id: Optional[str] = None,
        predicted_class: Optional[str] = None,
        confidence: Optional[float] = None,
        is_high_risk: Optional[bool] = None,
        input_summary: Optional[Dict[str, Any]] = None,
        response_summary: Optional[Dict[str, Any]] = None,
        db_path: Optional[Path] = None,
    ) -> int:
        return db.insert_record(
            endpoint=endpoint,
            request_id=request_id,
            predicted_class=predicted_class,
            confidence=confidence,
            is_high_risk=is_high_risk,
            input_summary=input_summary,
            response_summary=response_summary,
            db_path=db_path,
        )

    def get_records(self, limit: int = 100, endpoint: Optional[str] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        return db.get_records(limit=limit, endpoint=endpoint, db_path=db_path)


class SettingsRepository:
    """Persistence for app settings."""

    def get(self, key: str, db_path: Optional[Path] = None) -> Optional[str]:
        return db.get_setting(key, db_path)

    def set(self, key: str, value: str, db_path: Optional[Path] = None) -> None:
        db.set_setting(key, value, db_path)


# Convenience: default instances for use by API (can be replaced with DI)
records_repo = RecordsRepository()
settings_repo = SettingsRepository()
