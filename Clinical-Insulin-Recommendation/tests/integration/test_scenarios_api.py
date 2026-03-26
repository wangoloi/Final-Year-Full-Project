"""Test 7 recommendation scenarios against the API. Run: python tests/integration/test_scenarios_api.py"""
import sys
try:
    import requests
except ImportError:
    print("pip install requests"); sys.exit(1)
API = "http://localhost:8000/api"
SCENARIOS = [
    {"name": "1. Young adult, normal glucose", "body": {"age": 25, "gender": "Male", "food_intake": "Medium", "previous_medications": "None", "glucose_level": 95, "BMI": 22, "HbA1c": 5.5, "weight": 70}},
    {"name": "2. Elevated glucose, oral meds", "body": {"age": 45, "gender": "Female", "food_intake": "High", "previous_medications": "Oral", "medication_name": "Metformin", "glucose_level": 165, "BMI": 28, "HbA1c": 7.8, "weight": 82}},
    {"name": "3. Low glucose, insulin user", "body": {"age": 55, "gender": "Male", "food_intake": "Low", "previous_medications": "Insulin", "glucose_level": 68, "BMI": 26, "HbA1c": 6.2, "weight": 75, "physical_activity": 8}},
    {"name": "4. High HbA1c, poor control", "body": {"age": 60, "gender": "Female", "food_intake": "High", "previous_medications": "Insulin", "glucose_level": 210, "BMI": 32, "HbA1c": 9.5, "weight": 88}},
    {"name": "5. Steady-state maintenance", "body": {"age": 40, "gender": "Male", "food_intake": "Medium", "previous_medications": "None", "glucose_level": 110, "BMI": 24, "HbA1c": 6.0, "weight": 78}},
    {"name": "6. Elderly, low activity", "body": {"age": 72, "gender": "Female", "food_intake": "Low", "previous_medications": "Oral", "medication_name": "Glipizide", "glucose_level": 140, "BMI": 27, "HbA1c": 7.2, "weight": 65, "physical_activity": 2}},
    {"name": "7. Critical high glucose", "body": {"age": 35, "gender": "Male", "food_intake": "High", "previous_medications": "Insulin", "glucose_level": 380, "BMI": 30, "HbA1c": 10.2, "weight": 95}},
]
def main():
    print("Testing GlucoSense API (7 scenarios)...\n")
    ok = 0
    for s in SCENARIOS:
        try:
            r = requests.post(f"{API}/recommend", json=s["body"], timeout=60)
            data = r.json() if r.ok else {}
            if r.ok:
                pred, conf = data.get("predicted_class", "?"), data.get("confidence", 0) * 100
                action, risk = data.get("dosage_action", "?"), "HIGH RISK" if data.get("is_high_risk") else "ok"
                print(f"{s['name']}\n  -> {pred} | {action} | conf={conf:.0f}% | {risk}\n")
                ok += 1
            else:
                print(f"{s['name']}\n  -> ERROR {r.status_code}: {data.get('detail', data)}\n")
        except Exception as e:
            print(f"{s['name']}\n  -> EXCEPTION: {e}\n")
    print(f"Passed: {ok}/{len(SCENARIOS)}")
    return 0 if ok == len(SCENARIOS) else 1
if __name__ == "__main__":
    sys.exit(main())
