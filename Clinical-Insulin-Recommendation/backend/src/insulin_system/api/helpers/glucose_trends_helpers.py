"""
Glucose trends series builder for chart API.

Single responsibility: transform DB rows into chart series format.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from .route_data import CHART_MISSING_GLUCOSE_DEFAULT


def _normalize_ts_string(s: str) -> str:
    """SQLite / Python ``str(datetime)`` use a space between date and time; JS needs ``T`` for reliable parsing."""
    s = s.strip()
    if not s:
        return s
    # First whitespace run after YYYY-MM-DD → single T (handles str(dt) and odd spacing).
    return re.sub(r"^(\d{4}-\d{2}-\d{2})\s+(\d)", r"\1T\2", s, count=1)


def _iso_utc_for_client(ts: Any) -> str:
    """UTC ISO 8601 string that JavaScript ``Date`` parses reliably (Z suffix)."""
    if ts is None:
        return ""
    s = _normalize_ts_string(str(ts))
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        # Last resort: common TEXT patterns from SQLite / legacy rows
        m = re.match(
            r"^(\d{4}-\d{2}-\d{2})[T ](\d{1,2}:\d{2}:\d{2})(?:\.(\d+))?",
            s,
        )
        if m:
            try:
                base = f"{m.group(1)} {m.group(2)}"
                dt = datetime.strptime(base, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                return dt.isoformat().replace("+00:00", "Z")
            except Exception:
                pass
        return s


def build_trend_series(rows: List[Dict[str, Any]], hours: int = 24) -> List[Dict[str, Any]]:
    """Build chart series from glucose readings. Deduplicates by timestamp + patient.

    Each point includes ``time`` (HH:MM:SS), ``label`` (axis-friendly date/time for the window),
    ``iso`` (ISO reading time), and optional ``patient_id`` when present on the row.
    """
    seen: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []

    for r in rows:
        ts = r.get("reading_at")
        time_label = _format_time_label(ts)
        raw_pid = r.get("patient_id")
        try:
            pid = int(raw_pid) if raw_pid is not None else None
        except (TypeError, ValueError):
            pid = None
        key = f"{ts}|{pid if pid is not None else ''}"

        if key not in seen:
            seen[key] = len(out)
            out.append(
                {
                    "time": time_label,
                    "label": _format_display_label(ts, hours),
                    "iso": _iso_utc_for_client(ts),
                    "actual": None,
                    "predicted": None,
                    "patient_id": pid,
                }
            )

        idx = seen[key]
        num_val = _safe_float(r.get("value"))
        if r.get("is_predicted"):
            out[idx]["predicted"] = num_val
        else:
            out[idx]["actual"] = num_val

    return _fill_missing_and_ensure_numeric(out)


def _format_time_label(ts: Any) -> str:
    """Short clock time (legacy field)."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return str(ts)[:19] if ts else ""


def _format_display_label(ts: Any, hours: int) -> str:
    """Human-readable tick label: always include calendar date + time for 12h/24h-style windows."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return str(ts)[:16] if ts else ""

    # Date + time so same-day vs overnight and multi-day windows are unambiguous.
    if hours <= 24:
        return dt.strftime("%b %d, %Y · %H:%M")
    if hours <= 72:
        return dt.strftime("%b %d, %Y %H:%M")
    return dt.strftime("%b %d, %Y %H:%M")


def _safe_float(val: Any) -> float:
    """Coerce to float; return default for null/invalid."""
    if val is None:
        return CHART_MISSING_GLUCOSE_DEFAULT
    try:
        return float(val)
    except (TypeError, ValueError):
        return CHART_MISSING_GLUCOSE_DEFAULT


def _fill_missing_and_ensure_numeric(series: List[Dict]) -> List[Dict]:
    """Fill null actual/predicted with each other; ensure no null for Recharts."""
    for row in series:
        if row["predicted"] is None and row["actual"] is not None:
            row["predicted"] = row["actual"]
        elif row["actual"] is None and row["predicted"] is not None:
            row["actual"] = row["predicted"]
        row["actual"] = row["actual"] if row["actual"] is not None else CHART_MISSING_GLUCOSE_DEFAULT
        row["predicted"] = row["predicted"] if row["predicted"] is not None else CHART_MISSING_GLUCOSE_DEFAULT
    return series
