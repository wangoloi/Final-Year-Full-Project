"""Clinical API authentication (middleware helpers)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend" / "src"))

from insulin_system.api.clinical_auth import verify_request_credentials


def _req(method: str, path: str, headers: dict | None = None) -> Request:
    hdrs = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "headers": hdrs,
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
    }
    return Request(scope)


def test_public_health_live_skips_auth(monkeypatch):
    monkeypatch.setenv("GLUCOSENSE_REQUIRE_AUTH", "true")
    monkeypatch.setenv("MEAL_PLAN_JWT_SECRET", "test-secret-for-jwt-must-be-long-enough-32")
    r = _req("GET", "/api/health/live")
    verify_request_credentials(r)


def test_strict_rejects_missing_credentials(monkeypatch):
    monkeypatch.setenv("GLUCOSENSE_REQUIRE_AUTH", "true")
    monkeypatch.delenv("GLUCOSENSE_API_KEY", raising=False)
    monkeypatch.setenv("MEAL_PLAN_JWT_SECRET", "test-secret-for-jwt-must-be-long-enough-32")
    r = _req("POST", "/api/recommend", {})
    with pytest.raises(HTTPException) as exc:
        verify_request_credentials(r)
    assert exc.value.status_code == 401


def test_api_key_accepted(monkeypatch):
    monkeypatch.setenv("GLUCOSENSE_REQUIRE_AUTH", "true")
    monkeypatch.setenv("GLUCOSENSE_API_KEY", "secret-key-123")
    monkeypatch.setenv("MEAL_PLAN_JWT_SECRET", "test-secret-for-jwt-must-be-long-enough-32")
    r = _req("GET", "/api/patients", {"X-API-Key": "secret-key-123"})
    verify_request_credentials(r)
    assert r.state.clinical_role == "clinician"


def test_jwt_patient_blocked_from_patients(monkeypatch):
    monkeypatch.setenv("GLUCOSENSE_REQUIRE_AUTH", "true")
    monkeypatch.delenv("GLUCOSENSE_API_KEY", raising=False)
    secret = "test-secret-for-jwt-must-be-long-enough-32"
    monkeypatch.setenv("MEAL_PLAN_JWT_SECRET", secret)
    token = jwt.encode(
        {"userId": 1, "role": "patient", "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )
    r = _req("GET", "/api/patients", {"Authorization": f"Bearer {token}"})
    with pytest.raises(HTTPException) as exc:
        verify_request_credentials(r)
    assert exc.value.status_code == 403


def test_jwt_clinician_allowed_on_patients(monkeypatch):
    monkeypatch.setenv("GLUCOSENSE_REQUIRE_AUTH", "true")
    monkeypatch.delenv("GLUCOSENSE_API_KEY", raising=False)
    secret = "test-secret-for-jwt-must-be-long-enough-32"
    monkeypatch.setenv("MEAL_PLAN_JWT_SECRET", secret)
    token = jwt.encode(
        {"userId": 1, "role": "clinician", "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )
    r = _req("GET", "/api/patients", {"Authorization": f"Bearer {token}"})
    verify_request_credentials(r)
    assert r.state.clinical_role == "clinician"
