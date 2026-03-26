"""
Audit logging for all predictions and recommendations.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

AUDIT_DIR = Path("outputs/audit")
AUDIT_FILE = "predictions.jsonl"


def _ensure_audit_dir() -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_DIR


def audit_log(
    event_type: str,
    request_id: Optional[str] = None,
    request_summary: Optional[Dict[str, Any]] = None,
    response_summary: Optional[Dict[str, Any]] = None,
    predicted_class: Optional[str] = None,
    confidence: Optional[float] = None,
    is_high_risk: Optional[bool] = None,
    audit_dir: Optional[Path] = None,
) -> None:
    """Append one audit entry (JSON line) to the audit log."""
    dir_path = Path(audit_dir) if audit_dir else _ensure_audit_dir()
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / AUDIT_FILE
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "request_id": request_id,
        "request_summary": request_summary,
        "response_summary": response_summary,
        "predicted_class": predicted_class,
        "confidence": confidence,
        "is_high_risk": is_high_risk,
    }
    entry = {k: v for k, v in entry.items() if v is not None}
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.warning("Audit log write failed: %s", e)


def log_prediction(
    endpoint: str,
    request_id: Optional[str],
    predicted_class: Optional[str],
    confidence: Optional[float],
    is_high_risk: Optional[bool] = None,
    request_summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a prediction or recommendation event."""
    audit_log(
        event_type=endpoint,
        request_id=request_id,
        request_summary=request_summary,
        response_summary={"predicted_class": predicted_class, "confidence": confidence, "is_high_risk": is_high_risk},
        predicted_class=predicted_class,
        confidence=confidence,
        is_high_risk=is_high_risk,
    )
