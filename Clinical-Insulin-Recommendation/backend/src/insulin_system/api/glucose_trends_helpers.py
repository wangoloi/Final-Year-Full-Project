"""
Glucose trends series builder for chart API.

Single responsibility: transform DB rows into chart series format.
"""
from datetime import datetime
from typing import Any, Dict, List

from .route_data import CHART_MISSING_GLUCOSE_DEFAULT


def build_trend_series(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build chart series from glucose readings. Deduplicates by timestamp."""
    seen: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []

    for r in rows:
        ts = r.get("reading_at")
        time_label = _format_time_label(ts)
        key = ts or time_label

        if key not in seen:
            seen[key] = len(out)
            out.append({"time": time_label, "actual": None, "predicted": None})

        idx = seen[key]
        num_val = _safe_float(r.get("value"))
        if r.get("is_predicted"):
            out[idx]["predicted"] = num_val
        else:
            out[idx]["actual"] = num_val

    return _fill_missing_and_ensure_numeric(out)


def _format_time_label(ts: Any) -> str:
    """Format timestamp for chart display."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return str(ts)[:19] if ts else ""


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
