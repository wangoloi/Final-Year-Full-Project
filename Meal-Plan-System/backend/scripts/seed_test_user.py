"""Seed demo users for local testing (Meal Plan API + GlucoSense portal use the same accounts).

Run from Meal-Plan-System/backend:
  python scripts/seed_test_user.py

Creates or updates:
  • Patient — email zoe@test.com, username Zoe, password Zoe123
  • Clinician — email clinician@demo.local, username ClinicianDemo, password DemoClinician123

GlucoSense sign-in accepts email or username with the matching password (via Meal Plan /api/auth/login).
"""
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_backend))

from api.shared.database import SessionLocal, init_db
from api.models import User
from api.core.rbac import ROLE_CLINICIAN, ROLE_PATIENT


def _upsert_user(
    db,
    *,
    username: str,
    email: str,
    password: str,
    first_name: str,
    role: str,
) -> str:
    u = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if u:
        u.set_password(password)
        u.role = role
        u.first_name = first_name or u.first_name
        return "updated"
    u = User(
        username=username,
        email=email,
        first_name=first_name,
        role=role,
    )
    u.set_password(password)
    db.add(u)
    return "created"


def main():
    init_db()
    db = SessionLocal()
    try:
        rows = [
            ("Zoe", "zoe@test.com", "Zoe123", "Zoe", ROLE_PATIENT),
            ("ClinicianDemo", "clinician@demo.local", "DemoClinician123", "Demo", ROLE_CLINICIAN),
        ]
        for username, email, pw, fn, role in rows:
            action = _upsert_user(db, username=username, email=email, password=pw, first_name=fn, role=role)
            print(f"{action}: {username} / {email} ({role})")
        db.commit()
        print("\nUse these on GlucoSense /login or Meal Plan /login (same credentials).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
