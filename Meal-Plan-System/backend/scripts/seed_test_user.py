"""Seed test user for manual testing.
Run (repo root):  python backend/scripts/seed_test_user.py
"""
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_backend))

from api.shared.database import SessionLocal, init_db
from api.models import User


def main():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(username="Zoe").first()
        if existing:
            print("User Zoe already exists.")
            return
        u = User(
            email="zoe@test.com",
            username="Zoe",
            first_name="Zoe",
        )
        u.set_password("Zoe123")
        db.add(u)
        db.commit()
        print("Created user: Zoe / Zoe123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
