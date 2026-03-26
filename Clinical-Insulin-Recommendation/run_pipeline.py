"""
Canonical ML pipeline for Smart Sensor Diabetes Monitoring (SmartSensor CSV).

Runs: load → validate → GroupShuffleSplit → preprocessing → tiered target →
models → StratifiedGroupKFold CV → composite scoring → best bundle + PDF report.

Usage:
  python run_pipeline.py
  python run_pipeline.py --data data/SmartSensor_DiabetesMonitoring.csv --skip-lstm

Legacy insulin_system evaluation (4-class insulin) is available via:
  python scripts/pipeline/run_evaluation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "backend" / "src"))

from smart_sensor_ml.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
