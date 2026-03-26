"""
Compatibility entrypoint: run the API from the repository root.

Prefer explicitly:
  uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

This shim keeps `uvicorn app:app` working for scripts and Docker.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app import app  # noqa: E402

__all__ = ["app"]
