"""
Seed the database with representative data on first run.

Creates sample notifications, messages, glucose readings, patient context,
and optional sample recommendation records so the UI shows data immediately.
"""
from __future__ import annotations

import hashlib
import logging
import math
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import (
    get_db_path,
    init_db,
    count_table,
    get_setting,
    insert_record,
    insert_alert,
    upsert_patient_context,
    set_setting,
    delete_patient_monitoring_rows,
    insert_glucose_reading,
    insert_dose_event,
)
from .patients import list_patients, create_patient, _ensure_patients_table, get_patient, patient_exists

logger = logging.getLogger(__name__)

# Named demo cohort for Patients page / monitoring demos (Uganda-style names).
DEMO_PATIENTS: List[Dict[str, Any]] = [
    {"name": "Samuel Okello", "gender": "Male", "date_of_birth": "1991-05-20", "medical_record_number": "MR-UG-001"},
    {"name": "John Mwesigwa", "gender": "Male", "date_of_birth": "1988-11-03", "medical_record_number": "MR-UG-002"},
    {"name": "Sarah Nakalema", "gender": "Female", "date_of_birth": "1995-02-14", "medical_record_number": "MR-UG-003"},
    {"name": "Judith Akelllo", "gender": "Female", "date_of_birth": "1993-07-22", "medical_record_number": "MR-UG-004"},
    {"name": "Simon Peter Tamale", "gender": "Male", "date_of_birth": "1990-09-09", "medical_record_number": "MR-UG-005"},
    {"name": "Musa Ssemadda", "gender": "Male", "date_of_birth": "1986-12-01", "medical_record_number": "MR-UG-006"},
]


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


def _count_glucose_for_patient(patient_id: int, db_path: Optional[Path] = None) -> int:
    path = get_db_path(db_path)
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM glucose_readings WHERE patient_id = ?", (patient_id,))
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def _seed_one_patient_monitoring(
    pid: int,
    name: str,
    idx: int,
    db_path: Optional[Path] = None,
    include_alert: bool = True,
) -> None:
    """Insert demo glucose curve, assessments, dose events, and optionally a warning alert for one patient."""
    nhash = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    now = datetime.now(timezone.utc)
    for step in range(36):
        t = now - timedelta(hours=step * 2)
        phase = (step / 36.0) * math.pi * 2
        base = 108 + (nhash % 42) + 48 * math.sin(phase + idx * 0.4) + ((nhash >> (step % 8)) & 15)
        value = int(max(68, min(310, base)))
        insert_glucose_reading(value, False, patient_id=pid, db_path=db_path, reading_at=t.replace(microsecond=0).isoformat())

    for days_ago, endpoint, pred, conf, risk, inp in (
        (0, "recommend", "steady", 0.86, False, {"glucose_level": 118, "iob": 0.02, "anticipated_carbs": 50, "glucose_trend": "steady", "age": 32, "food_intake": "Medium"}),
        (1, "recommend", "up", 0.81, False, {"glucose_level": 172, "iob": 0.015, "anticipated_carbs": 60, "glucose_trend": "rising", "age": 32, "food_intake": "High"}),
        (2, "predict", "down", 0.76, True, {"glucose_level": 76, "iob": 0.035, "anticipated_carbs": 12, "glucose_trend": "falling", "age": 32, "food_intake": "Low"}),
    ):
        insert_record(
            endpoint=endpoint,
            predicted_class=pred,
            confidence=conf,
            is_high_risk=risk,
            input_summary=inp,
            response_summary={"predicted_class": pred, "confidence": conf},
            patient_id=pid,
            db_path=db_path,
            created_at=(now - timedelta(days=days_ago)).isoformat(),
        )

    insert_dose_event(
        meal_bolus="4.5 U",
        total_dose="4.5 U",
        patient_id=pid,
        db_path=db_path,
        created_at=(now - timedelta(hours=5)).isoformat(),
    )
    insert_dose_event(
        correction_dose="2.0 U",
        total_dose="2.0 U",
        patient_id=pid,
        db_path=db_path,
        created_at=(now - timedelta(hours=20)).isoformat(),
    )

    if include_alert and idx < 3:
        first = name.split()[0] if name.strip() else "Patient"
        insert_alert(
            "warning",
            f"Glucose variability: {first}",
            "Recent readings show wider swings — review trend and dosing.",
            db_path=db_path,
            patient_id=pid,
        )


def ensure_patient_demo_monitoring(patient_id: int, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    If this patient has no monitoring data yet, insert the same demo bundle used for the named cohort
    (assessments, glucose series, doses). Idempotent when data already exists.
    """
    init_db(get_db_path(db_path).parent if db_path else None)
    _ensure_patients_table(db_path)
    if not patient_exists(patient_id, db_path):
        return {"ok": False, "error": "not_found", "seeded": False}
    if _count_glucose_for_patient(patient_id, db_path) > 0:
        return {"ok": True, "seeded": False, "reason": "already_has_monitoring"}
    row = get_patient(patient_id, db_path)
    name = (row or {}).get("name") or "Patient"
    idx = int(patient_id) % 6
    _seed_one_patient_monitoring(patient_id, name, idx, db_path, include_alert=True)
    logger.info("Ensured demo monitoring for patient", extra={"patient_id": patient_id})
    return {"ok": True, "seeded": True}


def seed_demo_cohort(db_path: Optional[Path] = None, force: bool = False) -> Dict[str, Any]:
    """
    Ensure named demo patients exist and populate monitoring data (glucose time series, assessments, doses, alerts).

    If force is True, replace existing monitoring rows for these patients. If False, skip patients who already
    have glucose readings (idempotent for demos).
    """
    init_db(get_db_path(db_path).parent if db_path else None)
    _ensure_patients_table(db_path)
    patients = list_patients(db_path)
    by_name = {p["name"]: p["id"] for p in patients}
    created_ids: List[int] = []

    for demo in DEMO_PATIENTS:
        name = demo["name"]
        if name in by_name:
            pid = by_name[name]
        else:
            pid = create_patient(
                name=name,
                condition="Type 1 Diabetes",
                date_of_birth=demo.get("date_of_birth"),
                gender=demo.get("gender"),
                medical_record_number=demo.get("medical_record_number"),
                db_path=db_path,
            )
            by_name[name] = pid
        created_ids.append(pid)

    n_seeded = 0
    for idx, (pid, demo) in enumerate(zip(created_ids, DEMO_PATIENTS)):
        name = demo["name"]

        if force:
            delete_patient_monitoring_rows(pid, db_path)
        elif _count_glucose_for_patient(pid, db_path) > 0:
            continue

        _seed_one_patient_monitoring(pid, name, idx, db_path, include_alert=True)
        n_seeded += 1

    logger.info("Demo cohort updated", extra={"patients": len(created_ids), "seeded_monitoring": n_seeded, "force": force})
    return {"patient_ids": created_ids, "monitoring_seeded_for": n_seeded, "force": force}


def _seed_patients(db_path: Optional[Path] = None) -> None:
    """On first run with no patients, load the named demo cohort instead of a single placeholder."""
    patients = list_patients(db_path)
    if len(patients) > 0:
        return
    seed_demo_cohort(db_path=db_path, force=False)
    logger.info("Seeded demo patient cohort on empty database")


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
