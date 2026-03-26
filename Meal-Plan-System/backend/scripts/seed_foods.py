"""
Seed foods from CSV — FastAPI backend.
Usage (repo root):  python backend/scripts/seed_foods.py
Usage (backend):    cd backend && python scripts/seed_foods.py
"""
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_backend))

from api.shared.database import SessionLocal, init_db
from api.models import FoodItem
from api.utils.seed import load_foods_from_csv, seed_fallback, build_rag_store


def main():
    init_db()
    db = SessionLocal()
    try:
        n = load_foods_from_csv(db)
        if n > 0:
            print(f"Loaded {n} foods from CSV.")
        else:
            seed_fallback(db)
            print("Seeded fallback foods (CSV not found or empty).")
        build_rag_store(db)
        print("RAG knowledge base built.")
        count = db.query(FoodItem).count()
        print(f"Total food items: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
