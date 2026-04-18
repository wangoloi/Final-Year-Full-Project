"""Configuration - single source for env and paths."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Load env from repo root, then backend/ (backend overrides for local API dev)
    _backend_root = Path(__file__).resolve().parents[2]
    _repo_root = _backend_root.parent
    load_dotenv(_repo_root / ".env")
    load_dotenv(_backend_root / ".env", override=True)
except ImportError:
    pass


def _sqlite_url(file_path: Path) -> str:
    """Build a file-based SQLite URL. Windows backslashes break some drivers; use POSIX path."""
    return "sqlite:///" + file_path.resolve().as_posix()


def _db_path() -> str:
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    if os.name == "nt":
        appdata = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        db_dir = appdata / "Glocusense"
        db_dir.mkdir(exist_ok=True)
        return _sqlite_url(db_dir / "glocusense.db")
    base = Path(__file__).resolve().parents[2]
    (base / "instance").mkdir(exist_ok=True)
    return _sqlite_url(base / "instance" / "glocusense.db")


DATABASE_URL = _db_path()
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "dev-secret-change-in-production-32bytes-min"))
# Integrated dev runs the Meal Plan API on :8001 (GlucoSense clinical API uses :8000).
PORT = int(os.getenv("PORT", 8001))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower() or "development"
STRICT_STARTUP_VALIDATION = os.getenv("STRICT_STARTUP_VALIDATION", "").lower() in ("1", "true", "yes")

# GlucoSense portal embeds this app in an iframe and calls POST /api/auth/integration/glucosense
# with this header value. Dev default only — set GLUCOSENSE_EMBED_KEY in production.
GLUCOSENSE_EMBED_KEY = os.getenv("GLUCOSENSE_EMBED_KEY", "dev-embed-local-only")

# Typesense (food search). When TYPESENSE_HOST is empty, search uses SQL + RapidFuzz fallback.
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "").strip()
TYPESENSE_PORT = int(os.getenv("TYPESENSE_PORT", "8108"))
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http").strip().rstrip(":")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "xyz")
TYPESENSE_FOODS_COLLECTION = os.getenv("TYPESENSE_FOODS_COLLECTION", "foods")
TYPESENSE_CONNECTION_TIMEOUT_SECONDS = float(os.getenv("TYPESENSE_CONNECTION_TIMEOUT_SECONDS", "8"))

# LLM chatbot (RAG). Set OPENAI_API_KEY and/or OLLAMA_HOST.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
CHATBOT_MODEL = os.getenv("CHATBOT_MODEL", "gpt-4o-mini")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "").strip().rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "45"))

_backend_root = Path(__file__).resolve().parents[2]
(_backend_root / "instance").mkdir(exist_ok=True)
CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", str(_backend_root / "instance" / "chroma_nutrition")))
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_COLLECTION = os.getenv("RAG_COLLECTION", "nutrition_foods")
# Force old rule-based chatbot (ignore LLM) when "true"
CHATBOT_USE_LEGACY_ONLY = os.getenv("CHATBOT_USE_LEGACY_ONLY", "").lower() in ("1", "true", "yes")
# Prior user/assistant turns sent to the LLM (each message counts as one).
CHATBOT_HISTORY_MAX = max(0, int(os.getenv("CHATBOT_HISTORY_MAX", "20")))

# Transformer-based topic gate + linear SHAP explanations (sentence-transformers + sklearn).
CHATBOT_TOPIC_NLP_ENABLED = os.getenv("CHATBOT_TOPIC_NLP", "true").lower() in ("1", "true", "yes")
CHATBOT_TOPIC_THRESHOLD = float(os.getenv("CHATBOT_TOPIC_THRESHOLD", "0.38"))
CHATBOT_TOPIC_MAXSIM_FALLBACK = float(os.getenv("CHATBOT_TOPIC_MAXSIM_FALLBACK", "0.30"))

# Smart Sensor demo: synthetic monitoring CSV (glucose, HR, activity, etc.)
SMART_SENSOR_CSV_PATH = Path(
    os.getenv("SMART_SENSOR_CSV_PATH", str(_backend_root / "datasets" / "SmartSensor_DiabetesMonitoring.csv"))
).resolve()

# Optional: plain-text clinical / product prompt appended to the LLM system message (export Prompt.pdf → .txt, or paste).
_knowledge_dir = _backend_root / "knowledge"
_knowledge_dir.mkdir(exist_ok=True)
CLINICAL_PROMPT_SUPPLEMENT_PATH = Path(
    os.getenv(
        "CLINICAL_PROMPT_SUPPLEMENT_PATH",
        str(_knowledge_dir / "clinical_prompt_supplement.txt"),
    )
).resolve()
CLINICAL_PROMPT_SUPPLEMENT_MAX_CHARS = max(500, int(os.getenv("CLINICAL_PROMPT_SUPPLEMENT_MAX_CHARS", "8000")))


def is_production_like() -> bool:
    return APP_ENV in {"production", "staging"}


def runtime_validation() -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    weak_jwt = JWT_SECRET == "dev-secret-change-in-production-32bytes-min" or len(JWT_SECRET) < 32
    weak_embed = GLUCOSENSE_EMBED_KEY == "dev-embed-local-only" or len(GLUCOSENSE_EMBED_KEY) < 24

    if is_production_like() and weak_jwt:
        errors.append("JWT_SECRET must be set to a long random value in production-like environments.")
    elif weak_jwt:
        warnings.append("JWT_SECRET is using a development default.")

    if is_production_like() and weak_embed:
        errors.append("GLUCOSENSE_EMBED_KEY must be set to a long random value in production-like environments.")
    elif weak_embed:
        warnings.append("GLUCOSENSE_EMBED_KEY is using a development default.")

    if TYPESENSE_HOST and TYPESENSE_API_KEY == "xyz":
        if is_production_like():
            errors.append("TYPESENSE_API_KEY must be changed from the demo default when Typesense is enabled.")
        else:
            warnings.append("Typesense is enabled with the demo API key.")

    if not OPENAI_API_KEY and not OLLAMA_HOST:
        warnings.append("Chatbot LLM provider is not configured; chatbot will stay in fallback mode.")

    return {"errors": errors, "warnings": warnings}
