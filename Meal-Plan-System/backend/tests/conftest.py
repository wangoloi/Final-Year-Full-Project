"""Pytest configuration and fixtures - FastAPI."""
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# File-based DB so all connections share same schema (in-memory creates new DB per connection)
_fd, _test_db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
# Keep pytest fast: skip loading sentence-transformers + topic classifier unless overridden.
os.environ.setdefault("CHATBOT_TOPIC_NLP", "false")
# Deterministic chatbot assertions (rule path); unset or set false locally to exercise LLM in tests.
os.environ.setdefault("CHATBOT_USE_LEGACY_ONLY", "true")

# Absolute path before importing the app so api.core.config picks up a stable CSV location
# (avoids flaky sensor-demo tests when the process cwd differs from the backend folder).
_backend_dir = Path(__file__).resolve().parents[1]
_demo_csv = _backend_dir / "datasets" / "SmartSensor_DiabetesMonitoring.csv"
os.environ.setdefault("SMART_SENSOR_CSV_PATH", str(_demo_csv.resolve()))

from api.main import app
from api.shared.database import init_db, SessionLocal
from api.models import User, FoodItem


def pytest_sessionfinish(session, exitstatus):
    """Clean up temp test DB file."""
    try:
        if os.path.exists(_test_db_path):
            os.unlink(_test_db_path)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def reset_sensor_demo_cache():
    """Avoid flaky sensor-demo tests: reload CSV each test if a prior attempt cached an empty dataset."""
    from api.modules.sensor_demo import service

    service.reset_sensor_demo_cache()
    yield


@pytest.fixture
def client():
    """Create FastAPI test client (context manager runs lifespan)."""
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    """Yield DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create or get test user."""
    user = db_session.query(User).filter_by(email="test@example.com").first()
    if user:
        return user
    user = User(email="test@example.com", username="testuser", first_name="Test")
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers with JWT."""
    import jwt
    from api.core.config import JWT_SECRET
    token = jwt.encode({"userId": test_user.id, "exp": 9999999999}, JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
