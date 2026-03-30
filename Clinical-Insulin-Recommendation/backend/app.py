"""
GlucoSense Clinical Support - FastAPI backend (web API for the React app).

Repository layout:
  backend/app.py   ← this file (run via uvicorn)
  backend/src/     ← insulin_system (API, storage)
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
from starlette.requests import Request

_LAZY_ROUTES = os.environ.get("GLUCOSENSE_LAZY_ROUTES", "1").strip().lower() not in ("0", "false", "no")
_routes_loaded = False
_routes_lock = threading.Lock()

API_KEY = os.environ.get("GLUCOSENSE_API_KEY")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """DB seed + optional background bundle preload."""
    _log.info("GlucoSense starting.")
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
            _log.info("Inference bundle preloaded.")
        except Exception as e:
            _log.warning("Inference bundle not loaded (expected until a model is wired): %s", e)

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


# Liveness must not depend on the heavy routes module or SPA static mount (Vite + ApiGate poll this).
@app.get("/api/health/live", tags=["health"])
def api_health_live():
    return {"status": "ok", "live": True}


def _include_heavy_routes() -> None:
    """Import API routes once. Call from eager path or first request when lazy."""
    global _routes_loaded
    with _routes_lock:
        if _routes_loaded:
            return
        from insulin_system.api.routes import router as api_router  # noqa: E402

        app.include_router(api_router)
        _routes_loaded = True


if not _LAZY_ROUTES:
    _include_heavy_routes()
else:

    @app.middleware("http")
    async def _lazy_load_routes(request: Request, call_next):
        # Defer importing routes until first request so uvicorn binds quickly (Windows ML stack can be very slow to import).
        _include_heavy_routes()
        return await call_next(request)

# Serving frontend/dist at "/" breaks /api when the mount wins route matching (common after `npm run build`).
# Docker sets GLUCOSENSE_SERVE_SPA=1; local dev defaults off so Vite proxy always hits the API.
frontend_dist = ROOT / "frontend" / "dist"
_serve_spa = os.environ.get("GLUCOSENSE_SERVE_SPA", "0").strip().lower() in ("1", "true", "yes")
if frontend_dist.exists() and _serve_spa:
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
