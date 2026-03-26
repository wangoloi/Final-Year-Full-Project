"""
Glocusense API - FastAPI backend.
Microservice architecture: auth, search, chatbot, recommendations, glucose.
"""
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.shared.database import init_db, SessionLocal
from api.utils.seed import load_foods_from_csv, seed_fallback, build_rag_store
from api.modules.auth import router as auth_router
from api.modules.search import router as search_router
from api.modules.chatbot import router as chatbot_router
from api.modules.recommendations import router as recommendations_router
from api.modules.glucose import router as glucose_router
from api.modules.sensor_demo import router as sensor_demo_router
from api.core.logging_config import get_logger

logger = get_logger("api.main")


def _seed_worker() -> None:
    """Run CSV seed off the critical path so HTTP (e.g. /api/auth/register) is not blocked."""
    db = SessionLocal()
    try:
        n = load_foods_from_csv(db)
        if n == 0:
            seed_fallback(db)
        build_rag_store(db)
    except Exception as e:
        logger.error("Startup seed failed", extra={"error": str(e)})
    finally:
        db.close()
    try:
        from api.modules.search.typesense_search import sync_foods_index_from_db

        indexed = sync_foods_index_from_db()
        if indexed:
            logger.info("Typesense index synced after seed", extra={"documents": indexed})
    except Exception as e:
        logger.warning("Typesense index sync skipped or failed", extra={"error": str(e)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables immediately; seed foods in background so clients are not stuck waiting."""
    init_db()
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
    return {"status": "ok", "service": "glocusense-api"}


@app.get("/api/health")
def api_health():
    """Use via Vite proxy to confirm this Meal Plan API is what port 8000 is serving."""
    return {"status": "ok", "app": "glocusense-meal-plan"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
