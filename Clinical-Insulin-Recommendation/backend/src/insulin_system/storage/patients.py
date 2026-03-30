"""
Patient registration and retrieval.
Supports soft-delete (archive), restore, and permanent purge.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import get_db_path, init_db, set_setting

logger = logging.getLogger(__name__)

# Used with app_settings so we never re-insert "Sample Patient" after the user removes it.
SAMPLE_PATIENT_SEED_FLAG = "sample_patient_seed_done"


def _ensure_patients_table(db_path: Optional[Path] = None) -> None:
    """Create patients table and add patient_id to related tables if missing. Call after init_db."""
    path = get_db_path(db_path)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medical_record_number TEXT UNIQUE,
                name TEXT NOT NULL,
                date_of_birth TEXT,
                gender TEXT,
                condition TEXT NOT NULL DEFAULT 'Type 1 Diabetes',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        try:
            conn.execute("ALTER TABLE patients ADD COLUMN deleted_at TEXT NULL")
        except Exception:
            pass
        # Add patient_id to records if missing
        try:
            conn.execute("ALTER TABLE records ADD COLUMN patient_id INTEGER REFERENCES patients(id)")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE glucose_readings ADD COLUMN patient_id INTEGER REFERENCES patients(id)")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE dose_events ADD COLUMN patient_id INTEGER REFERENCES patients(id)")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE alerts ADD COLUMN patient_id INTEGER REFERENCES patients(id)")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE clinician_feedback ADD COLUMN patient_id INTEGER REFERENCES patients(id)")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(r: Any) -> Dict[str, Any]:
    d = dict(r)
    if d.get("deleted_at"):
        d["archived"] = True
    else:
        d["archived"] = False
    return d


def list_patients(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return active (non-archived) patients ordered by name."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at "
            "FROM patients WHERE deleted_at IS NULL ORDER BY name ASC"
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def list_archived_patients(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return archived patients (most recently archived first)."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at "
            "FROM patients WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC"
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_patient(
    patient_id: int,
    db_path: Optional[Path] = None,
    *,
    allow_archived: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return a patient by id. Default: active patients only."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return None
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        if allow_archived:
            cur = conn.execute(
                "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at "
                "FROM patients WHERE id = ?",
                (patient_id,),
            )
        else:
            cur = conn.execute(
                "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at "
                "FROM patients WHERE id = ? AND deleted_at IS NULL",
                (patient_id,),
            )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def create_patient(
    name: str,
    condition: str = "Type 1 Diabetes",
    date_of_birth: Optional[str] = None,
    gender: Optional[str] = None,
    medical_record_number: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Create a patient and return id."""
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    _ensure_patients_table(db_path)
    now = datetime.now(timezone.utc).isoformat()
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            """INSERT INTO patients (medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL)""",
            ((medical_record_number or "").strip() or None, name.strip(), date_of_birth, gender, condition, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_patient(
    patient_id: int,
    name: Optional[str] = None,
    condition: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    gender: Optional[str] = None,
    medical_record_number: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> bool:
    """Update an active patient. Returns True if updated."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return False
    now = datetime.now(timezone.utc).isoformat()
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "SELECT name, condition, date_of_birth, gender, medical_record_number FROM patients WHERE id = ? AND deleted_at IS NULL",
            (patient_id,),
        )
        row = cur.fetchone()
        if not row:
            return False
        existing = dict(zip(["name", "condition", "date_of_birth", "gender", "medical_record_number"], row))
        updates = {
            "name": name.strip() if name else existing["name"],
            "condition": condition if condition else existing["condition"],
            "date_of_birth": date_of_birth if date_of_birth is not None else existing["date_of_birth"],
            "gender": gender if gender is not None else existing["gender"],
            "medical_record_number": medical_record_number.strip() if medical_record_number else existing["medical_record_number"],
        }
        conn.execute(
            """UPDATE patients SET name=?, condition=?, date_of_birth=?, gender=?, medical_record_number=?, updated_at=?
               WHERE id=? AND deleted_at IS NULL""",
            (updates["name"], updates["condition"], updates["date_of_birth"], updates["gender"], updates["medical_record_number"] or None, now, patient_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def patient_exists(patient_id: int, db_path: Optional[Path] = None) -> bool:
    """True if patient exists and is active (not archived). Used for assessments."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return False
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "SELECT 1 FROM patients WHERE id = ? AND deleted_at IS NULL",
            (patient_id,),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def archive_patient(patient_id: int, db_path: Optional[Path] = None) -> bool:
    """Soft-delete (archive). Linked assessment rows are kept for restore. Returns True if archived."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return False
    import sqlite3
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "UPDATE patients SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now, now, patient_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return False
        try:
            set_setting(SAMPLE_PATIENT_SEED_FLAG, "1", db_path)
        except Exception:
            pass
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def restore_patient(patient_id: int, db_path: Optional[Path] = None) -> bool:
    """Un-archive a patient. Returns True if restored."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return False
    import sqlite3
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "UPDATE patients SET deleted_at = NULL, updated_at = ? WHERE id = ? AND deleted_at IS NOT NULL",
            (now, patient_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def purge_patient(patient_id: int, db_path: Optional[Path] = None) -> bool:
    """Permanently delete patient row and linked assessment data. Returns True if removed."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return False
    import sqlite3

    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute("SELECT 1 FROM patients WHERE id = ?", (patient_id,))
        if cur.fetchone() is None:
            return False

        try:
            conn.execute(
                "DELETE FROM clinician_feedback WHERE record_id IN (SELECT id FROM records WHERE patient_id = ?)",
                (patient_id,),
            )
        except Exception:
            pass
        for sql in (
            "DELETE FROM smart_sensor_predictions WHERE patient_id = ?",
            "DELETE FROM records WHERE patient_id = ?",
            "DELETE FROM glucose_readings WHERE patient_id = ?",
            "DELETE FROM dose_events WHERE patient_id = ?",
        ):
            try:
                conn.execute(sql, (patient_id,))
            except Exception as ex:
                logger.warning("purge_patient: %s skipped: %s", sql.split()[2], ex)
        for sql in (
            "DELETE FROM alerts WHERE patient_id = ?",
            "DELETE FROM clinician_feedback WHERE patient_id = ?",
        ):
            try:
                conn.execute(sql, (patient_id,))
            except Exception as ex:
                logger.warning("purge_patient: optional delete skipped: %s", ex)

        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        try:
            set_setting(SAMPLE_PATIENT_SEED_FLAG, "1", db_path)
        except Exception:
            pass
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Backwards compatibility: callers expecting hard delete should use purge_patient
def delete_patient(patient_id: int, db_path: Optional[Path] = None) -> bool:
    """Alias for archive_patient (soft delete)."""
    return archive_patient(patient_id, db_path)
