"""Pytest configuration and fixtures - FastAPI."""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# File-based DB so all connections share same schema (in-memory creates new DB per connection)
_fd, _test_db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
# Keep pytest fast: skip loading sentence-transformers + topic classifier unless overridden.
os.environ.setdefault("CHATBOT_TOPIC_NLP", "false")
os.environ.setdefault("SKIP_RAG_BUILD", "1")
# Deterministic chatbot assertions (rule path); unset or set false locally to exercise LLM in tests.
os.environ.setdefault("CHATBOT_USE_LEGACY_ONLY", "true")

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
    """Create or get test user (patient role)."""
    user = db_session.query(User).filter_by(email="test@example.com").first()
    if user:
        return user
    user = User(email="test@example.com", username="testuser", first_name="Test", role="patient")
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_clinician(db_session):
    """Clinician user for RBAC-protected routes (e.g. sensor-demo)."""
    user = db_session.query(User).filter_by(email="clinician@example.com").first()
    if user:
        return user
    user = User(email="clinician@example.com", username="clinician_test", first_name="Clinical", role="clinician")
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers with JWT (includes role claim)."""
    import jwt
    from api.core.config import JWT_SECRET
    token = jwt.encode(
        {"userId": test_user.id, "role": "patient", "exp": 9999999999},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_clinician(test_clinician):
    """JWT for clinician user."""
    import jwt
    from api.core.config import JWT_SECRET
    token = jwt.encode(
        {"userId": test_clinician.id, "role": "clinician", "exp": 9999999999},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
