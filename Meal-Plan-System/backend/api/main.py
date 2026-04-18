"""
Glocusense API - FastAPI backend.
Microservice architecture: auth, search, chatbot, recommendations, glucose.
"""
import os
import warnings

# Hugging Face hub: noisy FutureWarning about resume_download on some versions.
warnings.filterwarnings(
    "ignore",
    message=".*resume_download.*",
    category=FutureWarning,
    module=r"huggingface_hub.*",
)

# Chroma: disable telemetry early (avoids PostHog capture() signature errors with some dependency versions).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("CHROMA_TELEMETRY", "false")
# Hugging Face / transformers: skip TensorFlow + Flax unless explicitly needed (avoids Keras 3 / tf_keras errors).
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
os.environ.setdefault("USE_TF", "0")
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.models import FoodItem
from api.shared.database import init_db, SessionLocal
from api.utils.seed import load_foods_from_csv, seed_fallback, build_rag_store
from api.modules.auth import router as auth_router
from api.modules.search import router as search_router
from api.modules.chatbot import router as chatbot_router
from api.modules.recommendations import router as recommendations_router
from api.modules.glucose import router as glucose_router
from api.modules.sensor_demo import router as sensor_demo_router
from api.core import config
from api.core.logging_config import get_logger
from api.core.readiness import is_ready, reset, set_stage, set_status, set_warnings, snapshot

logger = get_logger("api.main")


def _seed_worker() -> None:
    """Run CSV seed off the critical path so HTTP (e.g. /api/auth/register) is not blocked."""
    db = SessionLocal()
    try:
        set_stage("foods", "running")
        n = load_foods_from_csv(db)
        if n == 0:
            seed_fallback(db)
        food_count = db.query(FoodItem).count()
        set_stage("foods", "ready", detail=f"Food catalog ready ({food_count} foods)")
        # Skip RAG in pytest / CI (set SKIP_RAG_BUILD=1) to avoid heavy imports and thread logging noise.
        if os.environ.get("SKIP_RAG_BUILD") != "1":
            set_stage("rag", "running")
            rag_docs = build_rag_store(db)
            if rag_docs == -1:
                set_status("degraded", "Startup warmup failed")
                set_stage("rag", "error", detail="RAG store build failed")
            else:
                detail = "RAG store built" if rag_docs else "RAG store initialized without documents"
                set_stage("rag", "ready", detail=detail)
        else:
            set_stage("rag", "skipped", detail="Skipped because SKIP_RAG_BUILD=1")
    except Exception as e:
        set_status("degraded", "Startup warmup failed")
        set_stage("foods", "error", detail=str(e))
        if snapshot()["stages"]["rag"]["status"] == "pending":
            set_stage("rag", "error", detail=str(e))
        logger.error("Startup seed failed", extra={"error": str(e)})
    finally:
        db.close()
    try:
        from api.modules.search.typesense_search import sync_foods_index_from_db

        set_stage("typesense", "running")
        indexed = sync_foods_index_from_db()
        if indexed:
            logger.info("Typesense index synced after seed", extra={"documents": indexed})
            set_stage("typesense", "ready", detail=f"Indexed {indexed} foods")
        else:
            set_stage("typesense", "skipped", detail="Typesense not configured or no foods to index")
    except Exception as e:
        set_status("degraded", "Startup warmup failed")
        set_stage("typesense", "error", detail=str(e))
        logger.warning("Typesense index sync skipped or failed", extra={"error": str(e)})
    if snapshot()["status"] != "degraded":
        set_status("ready", "Meal Plan API warmup complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables immediately; seed foods in background and publish readiness state."""
    reset()
    validation = config.runtime_validation()
    set_warnings(validation["warnings"])
    if validation["errors"]:
        set_stage("config", "error", detail="; ".join(validation["errors"]))
        if config.STRICT_STARTUP_VALIDATION:
            raise RuntimeError("; ".join(validation["errors"]))
        set_status("degraded", "Configuration warnings require attention")
    else:
        set_stage("config", "ready", detail="Configuration validated")

    init_db()
    set_stage("database", "ready", detail="Database initialized")
    threading.Thread(target=_seed_worker, name="glocusense-seed", daemon=True).start()
    yield


app = FastAPI(title="Glocusense API", version="1.0.0", lifespan=lifespan)

# Extra origins for production / Docker (comma-separated), e.g. https://app.example.com
_cors_extra = [o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]

# Do not combine allow_origins=["*"] with allow_credentials=True (invalid CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        *_cors_extra,
    ],
    # Any localhost port (Vite may use 5174+ if 5173 is busy)
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(search_router)
app.include_router(chatbot_router)
app.include_router(recommendations_router)
app.include_router(glucose_router)
app.include_router(sensor_demo_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "glocusense-api", "ready": is_ready()}


@app.get("/health/ready")
@app.get("/api/health/ready")
def readiness_health():
    state = snapshot()
    status_code = 200 if state.get("status") == "ready" else 503
    return JSONResponse(status_code=status_code, content=state)


@app.get("/api/health")
def api_health():
    """Use via Vite proxy to confirm this Meal Plan API is what port 8000 is serving."""
    state = snapshot()
    return {"status": "ok", "app": "glocusense-meal-plan", "ready": state.get("status") == "ready"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
