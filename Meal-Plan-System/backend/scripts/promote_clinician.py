"""
Set a user's role to clinician in the Meal Plan database.

Usage (from Meal-Plan-System, with DATABASE_URL / same env as API):
  python backend/scripts/promote_clinician.py user@example.com
"""
import os
import sys

from sqlalchemy import create_engine, text


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python promote_clinician.py <email>", file=sys.stderr)
        return 1
    email = sys.argv[1].strip().lower()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1
    engine = create_engine(url)
    with engine.begin() as conn:
        r = conn.execute(
            text("UPDATE users SET role = 'clinician' WHERE lower(email) = :e"),
            {"e": email},
        )
        print("Rows updated:", r.rowcount)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
