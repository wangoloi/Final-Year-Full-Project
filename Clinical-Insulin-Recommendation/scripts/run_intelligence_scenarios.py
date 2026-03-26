"""
Run 5 scenarios that showcase GlucoSense system intelligence.

Scenarios: target range, hyperglycemia correction, hypoglycemia reduction,
meal planning with carbs, and rising glucose trend.
"""
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

BASE = "http://127.0.0.1:8000"


def recommend(payload: dict) -> dict:
    r = requests.post(f"{BASE}/api/recommend", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    print("=" * 70)
    print("GlucoSense Intelligence Scenarios")
    print("=" * 70)

    base = {
        "age": 45,
        "gender": "Male",
        "family_history": "yes",
        "food_intake": "Medium",
        "previous_medications": "Insulin",
        "BMI": 26.5,
        "HbA1c": 7.2,
        "weight": 75,
        "insulin_sensitivity": 1.2,
        "physical_activity": 5.0,
    }

    scenarios = [
        {
            "name": "1. Target range (steady)",
            "desc": "Glucose 105 mg/dL, in target. No IOB, no carbs. Model should suggest no change.",
            "payload": {**base, "glucose_level": 105, "iob": 0, "anticipated_carbs": 0, "glucose_trend": "stable"},
        },
        {
            "name": "2. Hyperglycemia (up)",
            "desc": "Glucose 240 mg/dL, no IOB. Model should suggest increase/correction.",
            "payload": {**base, "glucose_level": 240, "iob": 0, "anticipated_carbs": 0, "glucose_trend": "stable"},
        },
        {
            "name": "3. Hypoglycemia (safety rejection)",
            "desc": "Glucose 55 mg/dL. CDS must REJECT dose recommendation, suggest carbs.",
            "payload": {**base, "glucose_level": 55, "iob": 0, "anticipated_carbs": 0, "glucose_trend": "falling"},
        },
        {
            "name": "4. Meal planning (up)",
            "desc": "Glucose 140 mg/dL, 60g carbs planned. Model considers meal + correction.",
            "payload": {**base, "glucose_level": 140, "iob": 0, "anticipated_carbs": 60, "glucose_trend": "stable", "icr": 10, "isf": 50},
        },
        {
            "name": "5. Rising trend (up)",
            "desc": "Glucose 180 mg/dL, rising. Model should factor trend.",
            "payload": {**base, "glucose_level": 180, "iob": 0.5, "anticipated_carbs": 0, "glucose_trend": "rising"},
        },
    ]

    for s in scenarios:
        print(f"\n{s['name']}")
        print(f"  {s['desc']}")
        try:
            resp = recommend(s["payload"])
            pred = resp.get("predicted_class", "?")
            conf = resp.get("confidence_level", 0)
            suggestion = resp.get("suggested_action", "")[:200]
            meal = resp.get("meal_bolus_units")
            correction = resp.get("correction_dose_units")
            status = resp.get("status", "?")
            print(f"  -> Predicted: {pred} (confidence: {conf:.2f})")
            print(f"  -> Status: {status}")
            if meal is not None:
                print(f"  -> Meal bolus: {meal:.1f} units")
            if correction is not None:
                print(f"  -> Correction: {correction:.1f} units")
            print(f"  -> Suggestion: {suggestion}...")
        except Exception as e:
            print(f"  -> Error: {e}")

    print("\n" + "=" * 70)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
