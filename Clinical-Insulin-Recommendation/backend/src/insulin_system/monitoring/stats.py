"""
Production monitoring: track prediction distribution and basic stats.
Enables drift detection and model performance tracking.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MONITOR_LOG_DIR = Path("outputs/monitoring")
MONITOR_LOG_FILE = "prediction_stats.jsonl"


@dataclass
class PredictionStats:
    """Single prediction record for monitoring."""

    timestamp: str
    predicted_class: str
    confidence: float
    is_high_risk: bool
    endpoint: str = "recommend"


_monitor: Optional["PredictionMonitor"] = None


def get_monitor() -> "PredictionMonitor":
    """Get or create the global prediction monitor."""
    global _monitor
    if _monitor is None:
        _monitor = PredictionMonitor()
    return _monitor


class PredictionMonitor:
    """
    Tracks prediction distribution and writes to JSONL for analysis.
    Use log_prediction() to record; get_stats() for recent summary.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self._log_dir = log_dir or MONITOR_LOG_DIR
        self._log_path = self._log_dir / MONITOR_LOG_FILE
        self._buffer: List[PredictionStats] = []
        self._max_buffer = 1000

    def log_prediction(
        self,
        predicted_class: str,
        confidence: float,
        is_high_risk: bool = False,
        endpoint: str = "recommend",
    ) -> None:
        """Record a prediction for monitoring."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            stats = PredictionStats(
                timestamp=datetime.now(timezone.utc).isoformat(),
                predicted_class=str(predicted_class).lower(),
                confidence=float(confidence),
                is_high_risk=bool(is_high_risk),
                endpoint=endpoint,
            )
            self._buffer.append(stats)
            if len(self._buffer) >= self._max_buffer:
                self._flush()
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(stats)) + "\n")
        except Exception as e:
            logger.warning("Monitoring log failed: %s", e)

    def _flush(self) -> None:
        """Flush buffer (no-op; we write immediately)."""
        self._buffer.clear()

    def get_recent_stats(self, n: int = 100) -> Dict[str, Any]:
        """Return summary of last n predictions from buffer or log."""
        samples = self._buffer[-n:] if len(self._buffer) >= n else self._buffer
        if not samples:
            try:
                if self._log_path.exists():
                    lines = self._log_path.read_text(encoding="utf-8").strip().split("\n")
                    lines = [l for l in lines if l.strip()][-n:]
                    samples = []
                    for line in lines:
                        try:
                            d = json.loads(line)
                            samples.append(PredictionStats(**d))
                        except Exception:
                            pass
            except Exception:
                pass
        if not samples:
            return {"n": 0, "class_distribution": {}, "avg_confidence": 0, "high_risk_pct": 0}
        class_counts: Dict[str, int] = defaultdict(int)
        total_conf = 0.0
        high_risk_count = 0
        for s in samples:
            class_counts[s.predicted_class] += 1
            total_conf += s.confidence
            if s.is_high_risk:
                high_risk_count += 1
        return {
            "n": len(samples),
            "class_distribution": dict(class_counts),
            "avg_confidence": total_conf / len(samples) if samples else 0,
            "high_risk_pct": 100.0 * high_risk_count / len(samples) if samples else 0,
        }
