"""
GlucoSense Clinical Support - FastAPI backend (web API for the React app).

Repository layout:
  backend/app.py   ← this file (run via uvicorn)
  backend/src/     ← insulin_system, clinical_ml_pipeline
  frontend/        ← React (Vite)
  data/, outputs/, config/  ← repo root

Run from repo root:
  uvicorn app:app --reload --port 8000        # uses root app.py shim
  uvicorn backend.app:app --reload --port 8000

Optional: GLUCOSENSE_API_KEY enables API key auth (X-API-Key header).
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

# Suppress sklearn version mismatch warnings when loading saved models
warnings.filterwarnings("ignore", message=".*Trying to unpickle.*", category=UserWarning)

_log = logging.getLogger("glucosense")

BACKEND_ROOT = Path(__file__).resolve().parent
ROOT = BACKEND_ROOT.parent  # repository root (parent of backend/)
sys.path.insert(0, str(BACKEND_ROOT / "src"))

# DB and outputs paths are relative to repository root
import insulin_system.storage.db as _storage_db

_storage_db.set_project_root(ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from insulin_system.api.routes import router as api_router

API_KEY = os.environ.get("GLUCOSENSE_API_KEY")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """DB seed + background model preload."""
    _log.info("GlucoSense starting. First /api/recommend may take 30-60s while the model loads (one-time).")
    try:
        from insulin_system.storage import init_db, run_seed_if_needed

        init_db()
        run_seed_if_needed()
    except Exception as e:
        _log.warning("Startup DB init/seed failed (API will retry on demand): %s", e)

    def _preload():
        try:
            from insulin_system.api.engine import get_bundle

            get_bundle()
            _log.info("Model loaded and ready.")
        except Exception as e:
            _log.warning("Model preload failed (will load on first request): %s", e)

    threading.Thread(target=_preload, daemon=True).start()
    yield


app = FastAPI(
    title="GlucoSense Clinical Support API",
    description="Type 1 Diabetes Management - Insulin dosage prediction, recommendation, and explainability. "
    "This is a clinical decision support tool; all recommendations must be reviewed by a qualified healthcare professional.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except ImportError:
    limiter = None


app.include_router(api_router)

frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.exists():
    static = StaticFiles(directory=str(frontend_dist), html=True)
    app.mount("/", static, name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "message": "GlucoSense Clinical Support",
            "subtitle": "Type 1 Diabetes Management — FastAPI + React (Vite)",
            "docs": "/docs",
            "api": "/api",
            "hint": "Dev UI: cd frontend && npm run dev → http://localhost:5173",
        }
