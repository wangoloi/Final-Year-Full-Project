"""Shared FastAPI dependencies."""
from typing import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
import jwt

from api.shared.database import get_db
from api.models import User
from api.core.config import JWT_SECRET
from api.core.logging_config import get_logger
from api.core.rbac import user_has_any_role, ROLE_CLINICIAN, ROLE_PATIENT

logger = get_logger("api.dependencies")


def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT, return current user (DB is source of truth for role)."""
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        raise HTTPException(401, "Missing or invalid token")

    token = authorization[7:]
    secret = JWT_SECRET if isinstance(JWT_SECRET, str) else str(JWT_SECRET)
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        raise HTTPException(401, "Invalid token")

    user_id = payload.get("userId")
    if not user_id:
        raise HTTPException(401, "Invalid token")

    user = db.get(User, user_id)
    if not user:
        logger.warning("User not found", extra={"user_id": user_id})
        raise HTTPException(401, "User not found")

    return user


def require_roles(*allowed: str) -> Callable[..., User]:
    """Dependency factory: allow only users whose role is in allowed (admin always allowed)."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if not user_has_any_role(user.role, *allowed):
            raise HTTPException(403, "Insufficient permissions")
        return user

    return _dep


require_clinician = require_roles(ROLE_CLINICIAN)
require_patient_or_clinician = require_roles(ROLE_PATIENT, ROLE_CLINICIAN)
