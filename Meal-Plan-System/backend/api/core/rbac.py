"""Role constants and helpers — source of truth is User.role in the database."""
from __future__ import annotations

ROLE_PATIENT = "patient"
ROLE_CLINICIAN = "clinician"
ROLE_ADMIN = "admin"
VALID_ROLES = frozenset({ROLE_PATIENT, ROLE_CLINICIAN, ROLE_ADMIN})


def normalize_role(value: str | None) -> str:
    r = (value or ROLE_PATIENT).strip().lower()
    return r if r in VALID_ROLES else ROLE_PATIENT


def user_has_any_role(user_role: str | None, *allowed: str) -> bool:
    r = normalize_role(user_role)
    if r == ROLE_ADMIN:
        return True
    return r in {normalize_role(a) for a in allowed}
