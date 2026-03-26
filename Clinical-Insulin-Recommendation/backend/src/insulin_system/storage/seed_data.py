"""
Seed the database with representative data on first run.

Creates sample notifications, messages, glucose readings, patient context,
and optional sample recommendation records so the UI shows data immediately.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .db import (
    get_db_path,
    init_db,
    count_table,
    get_setting,
    insert_record,
    insert_alert,
    upsert_patient_context,
    set_setting,
)
from .patients import list_patients, create_patient, _ensure_patients_table

logger = logging.getLogger(__name__)


def _seed_notifications(db_path: Optional[Path] = None) -> None:
    import sqlite3
    path = get_db_path(db_path)
    if count_table("notifications", db_path) > 0:
        return
    conn = sqlite3.connect(str(path))
    try:
        now = datetime.now(timezone.utc)
        rows = [
            (now.isoformat(), "Patient glucose trending above target. Review recommended.", 1),
            ((now - timedelta(minutes=30)).isoformat(), "Weekly summary ready for review.", 0),
            ((now - timedelta(hours=2)).isoformat(), "New lab result: HbA1c uploaded.", 1),
        ]
        for created_at, text, unread in rows:
            conn.execute(
                "INSERT INTO notifications (created_at, text, unread) VALUES (?, ?, ?)",
                (created_at, text, unread),
            )
        conn.commit()
        logger.info("Seeded notifications")
    finally:
        conn.close()


def _seed_alerts(db_path: Optional[Path] = None) -> None:
    """Seed sample critical-condition alerts so Alerts page has initial content."""
    if count_table("alerts", db_path) > 0:
        return
    insert_alert("critical", "Sample: Hypoglycemia risk", "Glucose below 70 mg/dL requires immediate review.", db_path)
    insert_alert("warning", "Sample: High-risk recommendation", "Last recommendation flagged for clinician review.", db_path)
    logger.info("Seeded alerts")


def _seed_glucose_readings(db_path: Optional[Path] = None) -> None:
    """Do not seed glucose readings. Trend data comes only from user assessments (data entry)."""
    pass


def _seed_patients(db_path: Optional[Path] = None) -> None:
    """Create a default patient if none exist."""
    patients = list_patients(db_path)
    if len(patients) > 0:
        return
    create_patient(
        name="Sample Patient",
        condition="Type 1 Diabetes",
        db_path=db_path,
    )
    logger.info("Seeded default patient")


def _seed_patient_context(db_path: Optional[Path] = None) -> None:
    upsert_patient_context(
        name="Current Patient",
        condition="Type 1 Diabetes",
        glucose=128,
        carbohydrates=45,
        activity_minutes=30,
        db_path=db_path,
    )
    logger.info("Seeded patient context")


def _seed_settings(db_path: Optional[Path] = None) -> None:
    if get_setting("units", db_path) is not None:
        return
    set_setting("units", "mg/dL", db_path)
    set_setting("theme", "light", db_path)
    set_setting("notifications_enabled", "true", db_path)
    logger.info("Seeded settings")


def _seed_sample_records(db_path: Optional[Path] = None) -> None:
    if count_table("records", db_path) > 0:
        return
    # IOB in mL (U-100: 1 unit = 0.01 mL)
    samples = [
        ("recommend", "steady", 0.88, False, {"glucose_level": 112, "iob": 0.025, "anticipated_carbs": 45, "glucose_trend": "steady", "age": 34, "food_intake": "Medium"}),
        ("recommend", "up", 0.82, False, {"glucose_level": 168, "iob": 0, "anticipated_carbs": 60, "glucose_trend": "rising", "age": 42, "food_intake": "High"}),
        ("predict", "down", 0.79, True, {"glucose_level": 72, "iob": 0.04, "anticipated_carbs": 0, "glucose_trend": "falling", "age": 28, "food_intake": "Low"}),
    ]
    for endpoint, pred_class, conf, high_risk, input_summary in samples:
        insert_record(
            endpoint=endpoint,
            request_id=None,
            predicted_class=pred_class,
            confidence=conf,
            is_high_risk=high_risk,
            input_summary=input_summary,
            response_summary={"predicted_class": pred_class, "confidence": conf},
            db_path=db_path,
        )
    logger.info("Seeded sample records")


def run_seed_if_needed(db_path: Optional[Path] = None) -> None:
    """Run all seed steps. Idempotent: only inserts when tables are empty where applicable."""
    init_db(get_db_path(db_path).parent if db_path else None)
    _seed_patients(db_path)
    _seed_notifications(db_path)
    _seed_alerts(db_path)
    _seed_glucose_readings(db_path)
    _seed_patient_context(db_path)
    _seed_settings(db_path)
    _seed_sample_records(db_path)
