#!/usr/bin/env python3
"""Run Smart Sensor ML pipeline (see backend/src/smart_sensor_ml/cli.py)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend" / "src"))

from smart_sensor_ml.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
