#!/usr/bin/env python3
"""
Seed foods from datasets/diabetic_diet_meal_plans_with_macros_GI.csv
Extracts unique dishes and inserts into PostgreSQL.
Run: python backend/database/seeds/seed_foods_from_csv.py (from repo root)
Requires: DATABASE_URL env var, psycopg2
"""

import os
import csv
import uuid
from pathlib import Path
from collections import defaultdict

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("Install psycopg2: pip install psycopg2-binary")
    raise

# parents: seeds -> database -> backend
BACKEND_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = BACKEND_ROOT / "datasets" / "diabetic_diet_meal_plans_with_macros_GI.csv"


def get_glycemic_category(gi: float) -> str:
    if gi is None or gi < 0:
        return "unknown"
    if gi <= 55:
        return "low"
    if gi <= 69:
        return "medium"
    return "high"


def load_unique_dishes() -> list[dict]:
    """Load unique dishes from CSV, averaging macros when dish appears multiple times."""
    dish_data = defaultdict(list)
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dish = row.get("Dish", "").strip()
            if not dish:
                continue
            try:
                cal = float(row.get("Calories", 0) or 0)
                pro = float(row.get("Protein", 0) or 0)
                carb = float(row.get("Carbs", 0) or 0)
                fat = float(row.get("Fat", 0) or 0)
                fiber = float(row.get("Fiber", 0) or 0)
                gi = float(row.get("Glycemic Index", 0) or 0)
            except (ValueError, TypeError):
                continue
            meal_type = (row.get("Meal") or "other").lower()
            dish_data[dish].append({
                "calories": cal, "protein": pro, "carbs": carb,
                "fat": fat, "fiber": fiber, "gi": gi, "meal": meal_type,
            })
    # Average values for each unique dish
    result = []
    for dish, entries in dish_data.items():
        n = len(entries)
        result.append({
            "name": dish,
            "category": entries[0]["meal"],
            "calories": sum(e["calories"] for e in entries) / n,
            "protein": sum(e["protein"] for e in entries) / n,
            "carbs": sum(e["carbs"] for e in entries) / n,
            "fat": sum(e["fat"] for e in entries) / n,
            "fiber": sum(e["fiber"] for e in entries) / n,
            "glycemic_index": int(sum(e["gi"] for e in entries) / n),
            "tags": ["diabetic_friendly", get_glycemic_category(sum(e["gi"] for e in entries) / n) + "_gi"],
        })
    return result


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("Set DATABASE_URL environment variable")
    dishes = load_unique_dishes()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    rows = [
        (
            str(uuid.uuid4()),
            d["name"],
            d["category"],
            d["calories"],
            d["protein"],
            d["carbs"],
            d["fat"],
            d["fiber"],
            d["glycemic_index"],
            d["name"],
            d["tags"],
        )
    for d in dishes
    ]
    execute_values(
        cur,
        """INSERT INTO food (id, name, category, calories, protein, carbs, fat, fiber, glycemic_index, description, tags)
           VALUES %s""",
        rows,
        template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
    )
    conn.commit()
    conn.close()
    print(f"Seeded {len(rows)} unique foods from {CSV_PATH}")
