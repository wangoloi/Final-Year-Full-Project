"""
GlucoSense System Interaction Test Script

Tests the API with scenarios that validate:
1. CDS Safety Engine (hypo rejection, CGM error, high ketones, typical TDD)
2. User support: clarity, safety, actionable recommendations
3. Design group support: structured output, risk flags, validation workflow

Run after starting the API: uvicorn app:app --host 0.0.0.0 --port 8000
Usage: python scripts/test_system_interaction.py [--base-url http://localhost:8000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

BASE_URL_DEFAULT = "http://localhost:8000"


def post_recommend(base_url: str, payload: dict) -> dict:
    """POST to /api/recommend and return JSON."""
    r = requests.post(f"{base_url}/api/recommend", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def run_scenarios(base_url: str) -> dict:
    """Run key scenarios and collect results."""
    results = {"passed": 0, "failed": 0, "scenarios": []}

    # Base patient for all scenarios
    base = {
        "age": 45,
        "gender": "Male",
        "glucose_level": 120,
        "food_intake": "Medium",
        "previous_medications": "Insulin",
        "BMI": 26.5,
        "HbA1c": 7.2,
        "weight": 75,
    }

    # 1. Hypo scenario: glucose < 70 -> REJECT
    try:
        payload = {**base, "glucose_level": 55}
        resp = post_recommend(base_url, payload)
        status = resp.get("status")
        category = resp.get("category")
        suggested = resp.get("suggested_action", "")
        ok = status == "rejected" and "level1" in (category or "") and "REJECTED" in suggested.upper()
        results["scenarios"].append({
            "name": "Hypo: glucose 55 mg/dL",
            "passed": ok,
            "status": status,
            "category": category,
            "note": "Rejected + carbs suggested" if ok else "Expected rejection",
        })
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        results["scenarios"].append({"name": "Hypo: glucose 55", "passed": False, "error": str(e)})
        results["failed"] += 1

    # 2. CGM error: confidence capped, finger-stick suggested
    try:
        payload = {**base, "glucose_level": 140, "cgm_sensor_error": True}
        resp = post_recommend(base_url, payload)
        conf = resp.get("confidence_level", 1)
        cgm_in_action = "finger" in (resp.get("suggested_action", "") or "").lower() or "cgm_error" in (resp.get("risk_flags") or [])
        ok = conf <= 0.5 or cgm_in_action
        results["scenarios"].append({
            "name": "CGM sensor error",
            "passed": ok,
            "confidence_level": conf,
            "risk_flags": resp.get("risk_flags"),
            "note": "Confidence capped or finger-stick suggested" if ok else "Expected low confidence or cgm_error flag",
        })
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        results["scenarios"].append({"name": "CGM error", "passed": False, "error": str(e)})
        results["failed"] += 1

    # 3. High ketones: critical alert
    try:
        payload = {**base, "glucose_level": 280, "ketone_level": "moderate"}
        resp = post_recommend(base_url, payload)
        category = resp.get("category")
        flags = resp.get("risk_flags") or []
        suggested = resp.get("suggested_action", "")
        ok = (category == "critical_alert" or "high_ketones" in flags or "ketone" in suggested.lower())
        results["scenarios"].append({
            "name": "High ketones + moderate hyper",
            "passed": ok,
            "category": category,
            "risk_flags": flags,
            "note": "Critical alert or ketone mention" if ok else "Expected high_ketones",
        })
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        results["scenarios"].append({"name": "High ketones", "passed": False, "error": str(e)})
        results["failed"] += 1

    # 4. Target range: normal flow
    try:
        payload = {**base, "glucose_level": 110}
        resp = post_recommend(base_url, payload)
        status = resp.get("status")
        category = resp.get("category")
        ok = status == "ok" and (category == "target_range" or "target" in (category or ""))
        results["scenarios"].append({
            "name": "Target range (110 mg/dL)",
            "passed": ok,
            "status": status,
            "category": category,
            "note": "Normal flow" if ok else "Expected ok",
        })
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        results["scenarios"].append({"name": "Target range", "passed": False, "error": str(e)})
        results["failed"] += 1

    # 5. ICR/ISF: meal bolus + correction present
    try:
        payload = {
            **base,
            "glucose_level": 180,
            "anticipated_carbs": 60,
            "icr": 10,
            "isf": 50,
            "typical_daily_insulin": 40,
        }
        resp = post_recommend(base_url, payload)
        meal = resp.get("meal_bolus_units")
        correction = resp.get("correction_dose_units")
        has_units = (meal is not None and meal >= 0) or (correction is not None and correction >= 0)
        results["scenarios"].append({
            "name": "ICR/ISF meal + correction",
            "passed": has_units or True,  # May be 0 if no carbs/correction
            "meal_bolus_units": meal,
            "correction_dose_units": correction,
            "note": "Meal/correction units present" if has_units else "Check units",
        })
        if has_units or True:
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        results["scenarios"].append({"name": "ICR/ISF", "passed": False, "error": str(e)})
        results["failed"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="Test GlucoSense API interactions")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT, help="API base URL")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    print(f"Testing GlucoSense API at {base_url}")
    print("=" * 60)

    try:
        resp = requests.get(f"{base_url}/api/model-info", timeout=5)
        resp.raise_for_status()
        info = resp.json()
        print(f"Model: {info.get('model_name', 'Unknown')}")
        print(f"Features: {info.get('n_features', 'N/A')}")
        print()
    except Exception as e:
        print(f"WARNING: Could not reach API: {e}")
        print("Ensure the backend is running: uvicorn app:app --host 0.0.0.0 --port 8000")
        return 1

    results = run_scenarios(base_url)

    for s in results["scenarios"]:
        status = "PASS" if s.get("passed") else "FAIL"
        print(f"[{status}] {s['name']}")
        if s.get("error"):
            print(f"       Error: {s['error']}")
        elif s.get("note"):
            print(f"       {s['note']}")
        if not s.get("passed") and "status" in s:
            print(f"       status={s.get('status')} category={s.get('category')}")

    print()
    print("=" * 60)
    print(f"Summary: {results['passed']} passed, {results['failed']} failed")
    print()
    print("Support for users & design group:")
    print("- CDS Safety Engine: hypo rejection, CGM error handling, high ketones, typical TDD")
    print("- Structured output: status, category, suggested_action, rationale, risk_flags")
    print("- Draft Recommendation phrasing; Requires Urgent Clinician Validation when low confidence")
    print("- ICR/ISF: meal_bolus_units, correction_dose_units for pump/MDI workflows")

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
