"""
SQLite database for storing prediction and recommendation records.

All API prediction, explain, and recommend responses are stored for audit
and retrieval. Database file: outputs/glucosense.db by default.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

DB_FILENAME = "glucosense.db"
# When set by app.py before routes load, paths are relative to project root (so backend works from any cwd).
_project_root: Optional[Path] = None


def set_project_root(root: Path) -> None:
    """Set project root so DB and outputs use paths relative to app location. Call from app.py before importing routes."""
    global _project_root
    _project_root = Path(root).resolve()


def _get_default_db_dir() -> Path:
    if _project_root is not None:
        return _project_root / "outputs"
    return Path("outputs")


def get_db_path(db_dir: Optional[Path] = None) -> Path:
    """Return the path to the SQLite database file."""
    d = Path(db_dir) if db_dir else _get_default_db_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / DB_FILENAME


def init_db(db_dir: Optional[Path] = None) -> None:
    """Create all tables (records, notifications, messages, glucose_readings, dose_events, app_settings) if they do not exist."""
    path = get_db_path(db_dir)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                request_id TEXT,
                predicted_class TEXT,
                confidence REAL,
                is_high_risk INTEGER,
                input_summary TEXT,
                response_summary TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE records ADD COLUMN patient_id INTEGER")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                text TEXT NOT NULL,
                unread INTEGER DEFAULT 1,
                notification_type TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE notifications ADD COLUMN notification_type TEXT")
            conn.commit()
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                sender TEXT NOT NULL,
                text TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS glucose_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reading_at TEXT NOT NULL,
                value INTEGER NOT NULL,
                is_predicted INTEGER DEFAULT 0
            )
        """)
        try:
            conn.execute("ALTER TABLE glucose_readings ADD COLUMN patient_id INTEGER")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dose_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                meal_bolus TEXT,
                correction_dose TEXT,
                total_dose TEXT,
                request_id TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE dose_events ADD COLUMN patient_id INTEGER")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                resolved INTEGER DEFAULT 0
            )
        """)
        try:
            conn.execute("ALTER TABLE alerts ADD COLUMN patient_id INTEGER")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patient_context (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                condition TEXT NOT NULL,
                glucose INTEGER,
                carbohydrates INTEGER,
                activity_minutes INTEGER,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clinician_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                record_id INTEGER,
                request_id TEXT,
                predicted_class TEXT,
                clinician_action TEXT,
                actual_dose_units REAL,
                override_reason TEXT,
                input_summary TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smart_sensor_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                patient_id INTEGER,
                measurement_time TEXT NOT NULL,
                meal_context TEXT,
                activity_context TEXT,
                predicted_tier TEXT,
                confidence REAL,
                probabilities_json TEXT
            )
        """)
        conn.commit()
        logger.info("Database initialized at %s", path)
    finally:
        conn.close()
    # Ensure patients table and patient_id columns exist (migration)
    try:
        from .patients import _ensure_patients_table
        _ensure_patients_table(path.parent if path else None)
    except Exception:
        pass


def insert_record(
    endpoint: str,
    request_id: Optional[str] = None,
    predicted_class: Optional[str] = None,
    confidence: Optional[float] = None,
    is_high_risk: Optional[bool] = None,
    input_summary: Optional[Dict[str, Any]] = None,
    response_summary: Optional[Dict[str, Any]] = None,
    patient_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Insert one record and return the row id."""
    from datetime import datetime, timezone
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            """INSERT INTO records (created_at, endpoint, request_id, predicted_class, confidence, is_high_risk, input_summary, response_summary, patient_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                endpoint,
                request_id,
                predicted_class,
                confidence,
                1 if is_high_risk else 0 if is_high_risk is False else None,
                json.dumps(input_summary, default=str) if input_summary is not None else None,
                json.dumps(response_summary, default=str) if response_summary is not None else None,
                patient_id,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_smart_sensor_prediction(
    measurement_time: str,
    predicted_tier: str,
    confidence: float,
    probabilities: Dict[str, Any],
    patient_id: Optional[int] = None,
    meal_context: Optional[str] = None,
    activity_context: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Persist Smart Sensor tier prediction for dashboards / trend analysis (§14)."""
    from datetime import datetime, timezone

    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3

    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            """INSERT INTO smart_sensor_predictions
               (created_at, patient_id, measurement_time, meal_context, activity_context, predicted_tier, confidence, probabilities_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                patient_id,
                measurement_time,
                meal_context,
                activity_context,
                predicted_tier,
                confidence,
                json.dumps(probabilities, default=str),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_records(limit: int = 100, patient_id: Optional[int] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return the most recent records (newest first). Optionally filter by patient_id."""
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        if patient_id is not None:
            cur = conn.execute(
                "SELECT id, created_at, endpoint, request_id, predicted_class, confidence, is_high_risk, input_summary, response_summary, patient_id FROM records WHERE patient_id = ? ORDER BY id DESC LIMIT ?",
                (patient_id, limit),
            )
        else:
            cur = conn.execute(
                "SELECT id, created_at, endpoint, request_id, predicted_class, confidence, is_high_risk, input_summary, response_summary, patient_id FROM records ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            if d.get("input_summary"):
                try:
                    d["input_summary"] = json.loads(d["input_summary"])
                except Exception:
                    pass
            if d.get("response_summary"):
                try:
                    d["response_summary"] = json.loads(d["response_summary"])
                except Exception:
                    pass
            d["is_high_risk"] = bool(d.get("is_high_risk"))
            out.append(d)
        return out
    finally:
        conn.close()


def delete_record(record_id: int, db_path: Optional[Path] = None) -> bool:
    """Delete one assessment record by primary key. Removes linked clinician_feedback rows. Returns True if a row was deleted."""
    path = get_db_path(db_path)
    if not path.exists():
        return False
    import sqlite3

    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DELETE FROM clinician_feedback WHERE record_id = ?", (record_id,))
        cur = conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def insert_notification(
    text: str,
    notification_type: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Insert a notification and return its id."""
    from datetime import datetime, timezone
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "INSERT INTO notifications (created_at, text, unread, notification_type) VALUES (?, ?, 1, ?)",
            (datetime.now(timezone.utc).isoformat(), text, notification_type),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_notifications_by_type(notification_type: str, db_path: Optional[Path] = None) -> None:
    """Delete all notifications with the given type."""
    path = get_db_path(db_path)
    if not path.exists():
        return
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DELETE FROM notifications WHERE notification_type = ?", (notification_type,))
        conn.commit()
    finally:
        conn.close()


def get_notifications(limit: int = 20, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    from datetime import datetime, timezone
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, created_at, text, unread, notification_type FROM notifications ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["unread"] = bool(d.get("unread"))
            ts = d.get("created_at")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    delta = now - dt
                    if delta.days > 0:
                        d["time"] = f"{delta.days} day(s) ago"
                    elif delta.seconds >= 3600:
                        d["time"] = f"{delta.seconds // 3600} hour(s) ago"
                    else:
                        d["time"] = f"{max(1, delta.seconds // 60)} min ago"
                except Exception:
                    d["time"] = ts
            out.append(d)
        return out
    finally:
        conn.close()


def mark_notifications_read(db_path: Optional[Path] = None) -> None:
    path = get_db_path(db_path)
    if not path.exists():
        return
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("UPDATE notifications SET unread = 0")
        conn.commit()
    finally:
        conn.close()


def get_messages(limit: int = 50, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, created_at, sender, text FROM messages ORDER BY id ASC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def insert_message(sender: str, text: str, db_path: Optional[Path] = None) -> int:
    from datetime import datetime, timezone
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "INSERT INTO messages (created_at, sender, text) VALUES (?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), sender, text),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_alert(
    severity: str,
    title: str,
    text: str,
    db_path: Optional[Path] = None,
) -> int:
    """Insert a critical-condition alert. severity: critical | warning."""
    from datetime import datetime, timezone
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "INSERT INTO alerts (created_at, severity, title, text, resolved) VALUES (?, ?, ?, ?, 0)",
            (datetime.now(timezone.utc).isoformat(), severity[:20], title[:200], text[:2000]),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_alerts(limit: int = 50, unresolved_only: bool = True, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return alerts (newest first)."""
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        if unresolved_only:
            cur = conn.execute(
                "SELECT id, created_at, severity, title, text, resolved FROM alerts WHERE resolved = 0 ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        else:
            cur = conn.execute(
                "SELECT id, created_at, severity, title, text, resolved FROM alerts ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["resolved"] = bool(d.get("resolved"))
            out.append(d)
        return out
    finally:
        conn.close()


def resolve_alert(alert_id: int, db_path: Optional[Path] = None) -> bool:
    """Mark a single alert as resolved. Returns True if updated."""
    path = get_db_path(db_path)
    if not path.exists():
        return False
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute("UPDATE alerts SET resolved = 1 WHERE id = ?", (alert_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def resolve_all_alerts(db_path: Optional[Path] = None) -> int:
    """Mark all unresolved alerts as resolved. Returns count updated."""
    path = get_db_path(db_path)
    if not path.exists():
        return 0
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute("UPDATE alerts SET resolved = 1 WHERE resolved = 0")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def get_glucose_readings(hours: int = 72, patient_id: Optional[int] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return glucose readings. Optionally filter by patient_id."""
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    from datetime import datetime, timezone, timedelta
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        if patient_id is not None:
            cur = conn.execute(
                "SELECT id, reading_at, value, is_predicted, patient_id FROM glucose_readings WHERE reading_at >= ? AND patient_id = ? ORDER BY reading_at ASC",
                (since, patient_id),
            )
        else:
            cur = conn.execute(
                "SELECT id, reading_at, value, is_predicted, patient_id FROM glucose_readings WHERE reading_at >= ? ORDER BY reading_at ASC",
                (since,),
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_glucose_points_from_records(
    patient_id: int,
    hours: Optional[int] = None,
    *,
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Glucose rows from assessment API records only: input_summary.glucose_level at created_at.

    Only endpoints that persist the assessment form (recommend / predict) are included.

    Pass ``limit`` (positive int) for the **most recent** N glucose readings (newest assessments first,
    then returned in chronological order for charting). Otherwise pass ``start_iso``/``end_iso`` or ``hours``.
    """
    from datetime import datetime, timezone, timedelta

    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3

    want_pid = int(patient_id)

    if limit is not None and int(limit) > 0:
        lim = min(max(int(limit), 1), 500)
        fetch_cap = min(max(lim * 40, lim), 2000)
        conn = sqlite3.connect(str(path))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT created_at, input_summary, patient_id AS record_patient_id
                FROM records
                WHERE patient_id = ?
                  AND input_summary IS NOT NULL
                  AND endpoint IN ('recommend', 'predict')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (want_pid, fetch_cap),
            )
            collected: List[Dict[str, Any]] = []
            for row in cur.fetchall():
                if len(collected) >= lim:
                    break
                row_pid = row["record_patient_id"]
                try:
                    row_pid_int = int(row_pid) if row_pid is not None else None
                except (TypeError, ValueError):
                    continue
                if row_pid_int != want_pid:
                    continue
                raw = row["input_summary"]
                if not raw:
                    continue
                try:
                    summ = json.loads(raw) if isinstance(raw, str) else raw
                except (json.JSONDecodeError, TypeError):
                    continue
                gl = summ.get("glucose_level")
                if gl is None or (isinstance(gl, str) and not str(gl).strip()):
                    continue
                try:
                    v = float(gl)
                except (TypeError, ValueError):
                    continue
                collected.append(
                    {
                        "reading_at": row["created_at"],
                        "value": v,
                        "is_predicted": False,
                        "patient_id": row_pid_int,
                    }
                )
            collected.reverse()
            return collected
        finally:
            conn.close()

    if start_iso is not None and end_iso is not None:
        range_clause = "AND created_at >= ? AND created_at < ?"
        range_params: tuple = (start_iso, end_iso)
    else:
        h = int(hours) if hours is not None else 24
        since = (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat()
        range_clause = "AND created_at >= ?"
        range_params = (since,)

    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            f"""
            SELECT created_at, input_summary, patient_id AS record_patient_id
            FROM records
            WHERE patient_id = ?
              {range_clause}
              AND input_summary IS NOT NULL
              AND endpoint IN ('recommend', 'predict')
            ORDER BY created_at ASC
            """,
            (patient_id, *range_params),
        )
        out: List[Dict[str, Any]] = []
        for row in cur.fetchall():
            row_pid = row["record_patient_id"]
            try:
                row_pid_int = int(row_pid) if row_pid is not None else None
            except (TypeError, ValueError):
                continue
            if row_pid_int != want_pid:
                continue
            raw = row["input_summary"]
            if not raw:
                continue
            try:
                summ = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                continue
            gl = summ.get("glucose_level")
            if gl is None or (isinstance(gl, str) and not str(gl).strip()):
                continue
            try:
                v = float(gl)
            except (TypeError, ValueError):
                continue
            out.append(
                {
                    "reading_at": row["created_at"],
                    "value": v,
                    "is_predicted": False,
                    "patient_id": row_pid_int,
                }
            )
        return out
    finally:
        conn.close()


def get_glucose_points_from_all_records(
    hours: Optional[int] = None,
    *,
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Glucose from all patients' assessment records (input_summary.glucose_level + created_at).

    Only recommend/predict assessment rows are included (same source as the per-patient trend).

    Pass ``limit`` for the **most recent** N glucose readings across all patients, or ``start_iso``/``end_iso`` or ``hours``.
    """
    from datetime import datetime, timezone, timedelta

    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3

    if limit is not None and int(limit) > 0:
        lim = min(max(int(limit), 1), 500)
        fetch_cap = min(max(lim * 40, lim), 2000)
        conn = sqlite3.connect(str(path))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT created_at, input_summary, patient_id
                FROM records
                WHERE patient_id IS NOT NULL
                  AND input_summary IS NOT NULL
                  AND endpoint IN ('recommend', 'predict')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (fetch_cap,),
            )
            collected: List[Dict[str, Any]] = []
            for row in cur.fetchall():
                if len(collected) >= lim:
                    break
                raw = row["input_summary"]
                if not raw:
                    continue
                try:
                    summ = json.loads(raw) if isinstance(raw, str) else raw
                except (json.JSONDecodeError, TypeError):
                    continue
                gl = summ.get("glucose_level")
                if gl is None or (isinstance(gl, str) and not str(gl).strip()):
                    continue
                try:
                    v = float(gl)
                except (TypeError, ValueError):
                    continue
                pid = row["patient_id"]
                collected.append(
                    {
                        "reading_at": row["created_at"],
                        "value": v,
                        "is_predicted": False,
                        "patient_id": int(pid) if pid is not None else None,
                    }
                )
            collected.reverse()
            return collected
        finally:
            conn.close()

    if start_iso is not None and end_iso is not None:
        range_clause = "AND created_at >= ? AND created_at < ?"
        range_params: tuple = (start_iso, end_iso)
    else:
        h = int(hours) if hours is not None else 24
        since = (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat()
        range_clause = "AND created_at >= ?"
        range_params = (since,)

    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            f"""
            SELECT created_at, input_summary, patient_id
            FROM records
            WHERE patient_id IS NOT NULL
              {range_clause}
              AND input_summary IS NOT NULL
              AND endpoint IN ('recommend', 'predict')
            ORDER BY created_at ASC
            """,
            range_params,
        )
        out: List[Dict[str, Any]] = []
        for row in cur.fetchall():
            raw = row["input_summary"]
            if not raw:
                continue
            try:
                summ = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                continue
            gl = summ.get("glucose_level")
            if gl is None or (isinstance(gl, str) and not str(gl).strip()):
                continue
            try:
                v = float(gl)
            except (TypeError, ValueError):
                continue
            pid = row["patient_id"]
            out.append(
                {
                    "reading_at": row["created_at"],
                    "value": v,
                    "is_predicted": False,
                    "patient_id": int(pid) if pid is not None else None,
                }
            )
        return out
    finally:
        conn.close()


def insert_glucose_reading(
    value: Union[int, float],
    is_predicted: bool = False,
    patient_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Append one glucose reading (from assessment or prediction). Returns row id."""
    from datetime import datetime, timezone
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "INSERT INTO glucose_readings (reading_at, value, is_predicted, patient_id) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), int(round(float(value))), 1 if is_predicted else 0, patient_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_dose_event(
    meal_bolus: Optional[str] = None,
    correction_dose: Optional[str] = None,
    total_dose: Optional[str] = None,
    request_id: Optional[str] = None,
    patient_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> int:
    from datetime import datetime, timezone
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            """INSERT INTO dose_events (created_at, meal_bolus, correction_dose, total_dose, request_id, patient_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), meal_bolus, correction_dose, total_dose, request_id, patient_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_dose_events(limit: int = 100, patient_id: Optional[int] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return dose events (newest first). Optionally filter by patient_id."""
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        if patient_id is not None:
            cur = conn.execute(
                "SELECT id, created_at, meal_bolus, correction_dose, total_dose, request_id, patient_id FROM dose_events WHERE patient_id = ? ORDER BY id DESC LIMIT ?",
                (patient_id, limit),
            )
        else:
            cur = conn.execute(
                "SELECT id, created_at, meal_bolus, correction_dose, total_dose, request_id, patient_id FROM dose_events ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_patient_context(db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    path = get_db_path(db_path)
    if not path.exists():
        return None
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT name, condition, glucose, carbohydrates, activity_minutes, updated_at FROM patient_context WHERE id = 1")
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_patient_context(
    name: str,
    condition: str,
    glucose: Optional[int] = None,
    carbohydrates: Optional[int] = None,
    activity_minutes: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> None:
    from datetime import datetime, timezone
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """INSERT INTO patient_context (id, name, condition, glucose, carbohydrates, activity_minutes, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET name=?, condition=?, glucose=?, carbohydrates=?, activity_minutes=?, updated_at=?""",
            (name, condition, glucose, carbohydrates, activity_minutes, now) * 2,
        )
        conn.commit()
    finally:
        conn.close()


def get_setting(key: str, db_path: Optional[Path] = None) -> Optional[str]:
    path = get_db_path(db_path)
    if not path.exists():
        return None
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_setting(key: str, value: str, db_path: Optional[Path] = None) -> None:
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    finally:
        conn.close()


def insert_clinician_feedback(
    record_id: Optional[int] = None,
    request_id: Optional[str] = None,
    predicted_class: Optional[str] = None,
    clinician_action: Optional[str] = None,
    actual_dose_units: Optional[float] = None,
    override_reason: Optional[str] = None,
    input_summary: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Record clinician override/feedback for model improvement. Returns row id."""
    from datetime import datetime, timezone
    import json
    path = get_db_path(db_path)
    init_db(path.parent if path else None)
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        inp_json = json.dumps(input_summary) if input_summary else None
        cur = conn.execute(
            """INSERT INTO clinician_feedback (created_at, record_id, request_id, predicted_class, clinician_action, actual_dose_units, override_reason, input_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), record_id, request_id, predicted_class, clinician_action, actual_dose_units, override_reason, inp_json),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_clinician_feedback(limit: int = 100, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve clinician feedback records for analysis."""
    import json
    path = get_db_path(db_path)
    if not path.exists():
        return []
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, created_at, record_id, request_id, predicted_class, clinician_action, actual_dose_units, override_reason, input_summary FROM clinician_feedback ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            if d.get("input_summary"):
                try:
                    d["input_summary"] = json.loads(d["input_summary"])
                except Exception:
                    pass
            out.append(d)
        return out
    finally:
        conn.close()


_ALLOWED_COUNT_TABLES = frozenset(
    {
        "records",
        "notifications",
        "messages",
        "glucose_readings",
        "dose_events",
        "alerts",
        "app_settings",
        "patient_context",
        "clinician_feedback",
        "patients",
    }
)


def count_table(table: str, db_path: Optional[Path] = None) -> int:
    if table not in _ALLOWED_COUNT_TABLES:
        raise ValueError(f"Invalid table name for count_table: {table!r}")
    path = get_db_path(db_path)
    if not path.exists():
        return 0
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]
    finally:
        conn.close()
