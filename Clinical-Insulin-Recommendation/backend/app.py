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
from insulin_system.api.clinical_auth import clinical_auth_middleware
from insulin_system.api.readiness import reset_readiness, update_readiness

API_KEY = os.environ.get("GLUCOSENSE_API_KEY")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """DB seed + synchronous model readiness warmup."""
    reset_readiness()
    _log.info("GlucoSense starting. Waiting for runtime model readiness before reporting ready.")
    try:
        from insulin_system.storage import init_db, run_seed_if_needed

        init_db()
        run_seed_if_needed()
        update_readiness(database={"status": "ready"})
    except Exception as e:
        update_readiness(
            status="degraded",
            database={"status": "error", "detail": str(e)},
            runtime={"status": "pending"},
        )
        _log.warning("Startup DB init/seed failed (API will retry on demand): %s", e)

    runtime_detail = {
        "active_pipeline": "legacy",
        "legacy_bundle": {"status": "pending"},
        "smart_sensor_bundle": {"status": "not_configured"},
    }
    try:
        from insulin_system.api.engine import get_bundle
        from insulin_system.api.smart_sensor_engine import (
            load_smart_sensor_bundle,
            smart_sensor_bundle_available,
        )

        if smart_sensor_bundle_available():
            runtime_detail["active_pipeline"] = "smart_sensor"
            runtime_detail["smart_sensor_bundle"] = {"status": "loading"}
            load_smart_sensor_bundle()
            runtime_detail["smart_sensor_bundle"] = {"status": "ready"}

        runtime_detail["legacy_bundle"] = {"status": "loading"}
        get_bundle()
        runtime_detail["legacy_bundle"] = {"status": "ready"}
        update_readiness(status="ready", runtime={"status": "ready"}, details=runtime_detail)
        _log.info(
            "Runtime ready. active_pipeline=%s legacy_bundle=%s smart_sensor_bundle=%s",
            runtime_detail["active_pipeline"],
            runtime_detail["legacy_bundle"]["status"],
            runtime_detail["smart_sensor_bundle"]["status"],
        )
    except Exception as e:
        runtime_detail.setdefault("error", str(e))
        if runtime_detail["legacy_bundle"]["status"] == "loading":
            runtime_detail["legacy_bundle"] = {"status": "error", "detail": str(e)}
        if runtime_detail["smart_sensor_bundle"]["status"] == "loading":
            runtime_detail["smart_sensor_bundle"] = {"status": "error", "detail": str(e)}
        update_readiness(status="degraded", runtime={"status": "error", "detail": str(e)}, details=runtime_detail)
        _log.warning("Runtime preload failed. Readiness will stay degraded until fixed: %s", e)

    yield

    update_readiness(status="stopped")


app = FastAPI(
    title="GlucoSense Clinical Support API",
    description="Type 1 Diabetes Management - Insulin dosage prediction, recommendation, and explainability. "
    "This is a clinical decision support tool; all recommendations must be reviewed by a qualified healthcare professional.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
)

# HTTP auth runs inside CORS: register CORS last so it is outermost (handles OPTIONS + response headers).
app.middleware("http")(clinical_auth_middleware)

# CORS: set CORS_ALLOW_ORIGINS to comma-separated list (e.g. https://your-app.netlify.app)
_default_cors = ",".join(
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
    ]
)
_cors_raw = os.environ.get("CORS_ALLOW_ORIGINS", _default_cors).strip()
_cors_list = [o.strip() for o in _cors_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list if _cors_list else [o.strip() for o in _default_cors.split(",")],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=bool(os.environ.get("CORS_ALLOW_CREDENTIALS", "").lower() in ("1", "true", "yes")),
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
