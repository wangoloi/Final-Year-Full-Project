"""
Clinical API authentication: X-API-Key and/or Meal Plan JWT (shared HS256 secret).

When GLUCOSENSE_REQUIRE_AUTH=true OR GLUCOSENSE_API_KEY is set, all /api/* routes
except /api/health/live require credentials. Development default: auth off.
"""
from __future__ import annotations

import os
from typing import Optional

import jwt
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

def _jwt_secret() -> str:
    """Must match Meal Plan API JWT_SECRET / MEAL_PLAN_JWT_SECRET for Bearer tokens."""
    return (
        os.environ.get("MEAL_PLAN_JWT_SECRET")
        or os.environ.get("JWT_SECRET")
        or os.environ.get("SECRET_KEY")
        or ""
    )


def _api_key() -> str:
    return (os.environ.get("GLUCOSENSE_API_KEY") or "").strip()


def auth_strict_enabled() -> bool:
    """Require API key or JWT when True."""
    if os.environ.get("GLUCOSENSE_REQUIRE_AUTH", "").lower() in ("1", "true", "yes"):
        return True
    return bool(_api_key())


def _public_api_paths() -> frozenset:
    # /api/meal-plan/sso — server proxies to Meal Plan API; embed key never sent from browser
    return frozenset({"/api/health/live", "/api/health/ready", "/api/meal-plan/sso"})


def _path_requires_clinician(method: str, path: str) -> bool:
    """Routes that must not be accessed with a patient JWT."""
    if path.startswith("/api/patients"):
        return True
    if path.startswith("/api/backup") or path.startswith("/api/backups"):
        return True
    if path.startswith("/api/notifications"):
        return True
    if path.startswith("/api/alerts"):
        return True
    if path == "/api/records" or path.startswith("/api/records"):
        return True
    if path.startswith("/api/settings"):
        return True
    if path.startswith("/api/patient-context"):
        return True
    if path.startswith("/api/glucose-trends"):
        return True
    if path.startswith("/api/dose"):
        return True
    if path.startswith("/api/monitoring"):
        return True
    if path.startswith("/api/health") and path not in {"/api/health/live", "/api/health/ready"}:
        return True
    if path.startswith("/api/feedback") and method.upper() == "GET":
        return True
    return False


def _decode_bearer(token: str) -> dict:
    secret = _jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Server missing MEAL_PLAN_JWT_SECRET / JWT_SECRET for Bearer validation",
        )
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from e


def verify_request_credentials(request: Request) -> None:
    """Validate API key or Bearer JWT; enforce clinician routes. Sets request.state.clinical_role."""
    path = request.url.path
    method = request.method.upper()

    if not path.startswith("/api") or path in _public_api_paths():
        return

    if not auth_strict_enabled():
        request.state.clinical_role = "anonymous"
        request.state.clinical_auth_bypass = True
        return

    api_key_hdr = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    auth = request.headers.get("Authorization") or ""

    role: Optional[str] = None
    auth_type: Optional[str] = None

    key = _api_key()
    if key and api_key_hdr == key:
        role = "clinician"
        auth_type = "api_key"
    elif auth.startswith("Bearer "):
        payload = _decode_bearer(auth[7:].strip())
        role = (payload.get("role") or "patient").lower()
        auth_type = "jwt"
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: send X-API-Key or Authorization: Bearer <JWT>",
        )

    if _path_requires_clinician(method, path) and role not in ("clinician", "admin"):
        raise HTTPException(status_code=403, detail="Clinician role required")

    request.state.clinical_role = role
    request.state.clinical_auth_type = auth_type
    request.state.clinical_auth_bypass = False


async def clinical_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    try:
        verify_request_credentials(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)
