# GlucoSense — Improvements Implemented

## Summary

The following improvements from the improvement suggestions have been implemented and tested.

---

## 1. Model Versioning & Rollback

- **`src/insulin_system/persistence/bundle.py`**: `save_best_model()` now saves versioned copies under `outputs/best_model/versions/v1/`, `v2/`, etc.
- **`list_model_versions()`**: Returns available version numbers for rollback.
- **`load_best_model(version=N)`**: Load a specific version instead of current.
- **`scripts/rollback_model.py`**: Rollback to a previous version.
  ```bash
  python scripts/rollback_model.py           # list versions
  python scripts/rollback_model.py --to 2   # rollback to v2
  ```

---

## 2. Feedback Loop for Retraining

- **`scripts/export_feedback_for_retraining.py`**: Exports clinician feedback from DB to CSV for model retraining.
  ```bash
  python scripts/export_feedback_for_retraining.py --out outputs/feedback_export.csv --limit 500
  ```

---

## 3. IOB Units Clarification

- **Engine & recommendation generator**: IOB display changed from "mL" to "units" for clinical clarity.
- **`config/clinical_thresholds.json`**: `iob_ml` section retained for backward compatibility; API accepts IOB in units.

---

## 4. Level 2 Hypoglycemia (<54 mg/dL)

- **`config/clinical_thresholds.json`**: Added `fast_acting_carbs_level2_grams: 20` for Level 2 hypo.
- **`src/insulin_system/domain/constants.py`**: `FAST_ACTING_CARBS_LEVEL2_GRAMS = 20`.
- **`src/insulin_system/api/engine.py`**: When `cds_category == "level2_hypoglycemia"`, suggests 20g carbs instead of 15g.

---

## 5. Stacking Safety (Rising + High IOB)

- **`src/insulin_system/recommendation/recommendation_generator.py`**: Added Case 2 in `_check_insulin_stacking()`:
  - When BG high + IOB significant + trend **rising** → reduce correction by 1 unit to avoid stacking (delayed absorption).

---

## 6. API: Batch Prediction, Rate Limiting

- **`POST /api/batch-recommend`**: Batch endpoint for up to 50 patients.
  ```json
  { "patients": [ {...}, {...} ] }
  ```
- **Rate limiting**: SlowAPI added to `requirements.txt`. Configure in `app.py` when enabled.
- **Optional API key**: Set `GLUCOSENSE_API_KEY` env var to enable `X-API-Key` header validation (documented in `app.py`).

---

## 7. Docker

- **`Dockerfile`**: Multi-stage build for GlucoSense API + frontend.
  ```bash
  docker build -t glucosense .
  docker run -p 8000:8000 glucosense
  ```
- Pre-build frontend: `cd frontend && npm run build` before `docker build`.

---

## 8. Frontend: Feedback Capture & Risk Flag Prominence

- **`frontend/src/components/FeedbackModal.jsx`**: Modal to record clinician override (action, actual dose, reason).
- **Dashboard**: "Report override" button after each recommendation.
- **Risk flags**: Prominent alert box when `result.risk_flags` is non-empty (hypoglycemia_alert, high_uncertainty, cgm_error, high_ketones).

---

## 9. Pediatric Rules

- Uganda Guideline: children <5 years — 0.5 IU/kg/day, refer to paediatrician. Already present in `recommendation_generator.py`; high-risk flag set when age < 5.

---

## Testing

- **`scripts/test_system_interaction.py`**: 5 scenarios (hypo, CGM error, ketones, target, ICR/ISF) — all pass.
- **`scripts/run_intelligence_scenarios.py`**: 5 intelligence scenarios — all pass.
- **Frontend**: Built successfully with `npm run build`.

---

## How to Run

```bash
# Backend only
uvicorn app:app --host 127.0.0.1 --port 8000

# Backend + frontend (dev)
.\scripts\windows\run_dev.ps1

# Or: backend, then frontend separately
# Terminal 1: uvicorn app:app --reload --port 8000
# Terminal 2: cd frontend && npm run dev
```

**Note**: Restart the backend after pulling these changes to enable the new `/api/batch-recommend` endpoint.
