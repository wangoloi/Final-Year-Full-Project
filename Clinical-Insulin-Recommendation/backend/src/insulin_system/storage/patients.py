"""
Patient registration and retrieval.
Stores patient demographics for assessment linkage.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import get_db_path, init_db

logger = logging.getLogger(__name__)


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
        try:
            conn.execute("ALTER TABLE patients ADD COLUMN deleted_at TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE patients ADD COLUMN mrn_backup TEXT")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def list_patients(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return all active (non-removed) patients ordered by name."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at "
            "FROM patients WHERE deleted_at IS NULL ORDER BY name ASC"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def list_removed_patients(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return patients removed from the register (soft-deleted), newest removal first."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at, mrn_backup "
            "FROM patients WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_patient(patient_id: int, db_path: Optional[Path] = None, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
    """Return a single patient by id. By default only active patients; include_deleted=True for restore flows."""
    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    if not path.exists():
        return None
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        if include_deleted:
            cur = conn.execute(
                "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at, mrn_backup "
                "FROM patients WHERE id = ?",
                (patient_id,),
            )
        else:
            cur = conn.execute(
                "SELECT id, medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at, deleted_at, mrn_backup "
                "FROM patients WHERE id = ? AND deleted_at IS NULL",
                (patient_id,),
            )
        row = cur.fetchone()
        return dict(row) if row else None
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
            """INSERT INTO patients (medical_record_number, name, date_of_birth, gender, condition, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
    """Update a patient. Returns True if updated."""
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
               WHERE id=?""",
            (updates["name"], updates["condition"], updates["date_of_birth"], updates["gender"], updates["medical_record_number"] or None, now, patient_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def patient_exists(patient_id: int, db_path: Optional[Path] = None) -> bool:
    """Check if an active (non-removed) patient exists."""
    return get_patient(patient_id, db_path, include_deleted=False) is not None


def delete_patient(patient_id: int, db_path: Optional[Path] = None) -> bool:
    """Soft-remove a patient from the register; monitoring data is kept for retrieval."""
    from .db import get_db_path, _conn_for_file

    _ensure_patients_table(db_path)
    if not patient_exists(patient_id, db_path):
        return False
    path = get_db_path(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn_for_file(path)
    try:
        cur = conn.execute("SELECT medical_record_number FROM patients WHERE id = ? AND deleted_at IS NULL", (patient_id,))
        row = cur.fetchone()
        if not row:
            return False
        mrn = row[0]
        cur = conn.execute(
            """UPDATE patients SET deleted_at = ?, updated_at = ?, mrn_backup = ?, medical_record_number = NULL
               WHERE id = ? AND deleted_at IS NULL""",
            (now, now, mrn, patient_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def restore_patient(patient_id: int, db_path: Optional[Path] = None) -> tuple[bool, Optional[str]]:
    """
    Put a soft-deleted patient back on the active list. Restores MRN from mrn_backup when present.
    Returns (True, None) on success, (False, error_code) on failure.
    """
    from .db import _conn_for_file

    _ensure_patients_table(db_path)
    path = get_db_path(db_path)
    row = get_patient(patient_id, db_path, include_deleted=True)
    if not row:
        return False, "not_found"
    # Only active patients have deleted_at NULL; use `is None` so edge cases like '' do not look "active".
    if row.get("deleted_at") is None:
        return False, "not_removed"

    mrn = row.get("mrn_backup")
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn_for_file(path)
    try:
        cur = conn.execute(
            """UPDATE patients SET deleted_at = NULL, updated_at = ?, medical_record_number = COALESCE(?, medical_record_number),
               mrn_backup = NULL WHERE id = ? AND deleted_at IS NOT NULL""",
            (now, mrn, patient_id),
        )
        conn.commit()
        if cur.rowcount > 0:
            return True, None
        return False, "restore_failed"
    except sqlite3.IntegrityError:
        conn.rollback()
        # Another active patient may already use this MRN — restore without reassigning MRN; keep mrn_backup for staff to copy.
        try:
            cur = conn.execute(
                """UPDATE patients SET deleted_at = NULL, updated_at = ?, medical_record_number = NULL,
                   mrn_backup = ? WHERE id = ? AND deleted_at IS NOT NULL""",
                (now, mrn, patient_id),
            )
            conn.commit()
            if cur.rowcount > 0:
                return True, "mrn_skipped_conflict"
        except sqlite3.IntegrityError:
            pass
        return False, "mrn_conflict"
    finally:
        conn.close()
