# GlucoSense Refactoring Summary

## Principles Applied

1. **Single Responsibility Principle** – Each function does one thing
2. **Small functions** – Under 20 lines, readable and testable
3. **Limited arguments** – 0–2 parameters where possible; no flag arguments
4. **Guard clauses and early returns** – Reduced nesting
5. **Data separated from logic** – Constants and structures in dedicated modules

---

## Backend Changes

### New Modules

| Module | Purpose |
|--------|---------|
| `api/route_data.py` | API constants and `build_input_summary` |
| `api/alert_helpers.py` | Critical alert insertion logic |
| `api/patient_context_helpers.py` | Patient context upsert from request body |
| `api/glucose_trends_helpers.py` | Chart series builder from DB rows |
| `api/shap_background.py` | SHAP background data loader |
| `api/recommend_response_builder.py` | Recommendation response assembly |

### Refactored Files

**`api/routes.py`**
- Removed inline helpers; uses new modules
- Removed unused constants (`COUNTERFACTUAL_TOP_K`, `PROBABILITY_BREAKDOWN_TOP_K`)
- Extracted `_safe_glucose_float`, `_record_glucose_trend`
- Guard clauses in route handlers

**`api/engine.py`**
- `run_recommend` split into:
  - `_safe_confidence`, `_safe_entropy`, `_prob_breakdown_from_proba`
  - `_patient_to_dict`, `_get_recommend_explanation_drivers`
  - `_log_mlflow_if_active`
- Response building moved to `recommend_response_builder`

**`api/validators.py`**
- Extracted `_check_numeric_warnings`, `_build_patient_row`, `_to_patient_input`, `_coerce_numeric`
- Data constants (`NUMERIC_KEYS`, `PATIENT_ROW_KEYS`) separated from logic

### Removed Unused Code

- `COUNTERFACTUAL_TOP_K`, `PROBABILITY_BREAKDOWN_TOP_K` from routes
- Unused imports (`AlertConfig`, `insert_alert`, `upsert_patient_context`, `PatientInput`)

---

## Frontend Changes

### New Modules

| Module | Purpose |
|--------|---------|
| `services/dashboardApi.js` | Recommendation, dose, feedback API calls |
| `services/clinicalApi.js` | Patient, notifications, alerts, records API calls |
| `utils/assessmentFormUtils.js` | Form validation, buildBody, initialForm (data + logic) |
| `components/dashboard/AssessmentForm.jsx` | Form fields and validation display |
| `components/dashboard/RecommendationResult.jsx` | Result cards (primary action, risk flags, insight, dosage, advice, factors, resources) |

### Refactored Files

**`pages/Dashboard.jsx`**
- Reduced from ~670 lines to ~170
- Uses `dashboardApi`, `assessmentFormUtils`, `AssessmentForm`, `RecommendationResult`
- Guard clauses in `getRecommendation` (early return on validation errors, on API error)

**`context/ClinicalContext.jsx`**
- Uses `clinicalApi` service instead of direct `apiFetch`
- Guard clauses: early return when `fetchPatientContext` returns null

**`pages/Alerts.jsx`**
- Uses `clinicalApi` for fetch, resolve, resolveAll

### Principles Applied

- **Single responsibility**: AssessmentForm (form only), RecommendationResult (display only), API services (HTTP only)
- **Small functions**: Validation split into `_validateAge`, `_validateGender`, etc.
- **Data separated from logic**: `assessmentFormUtils` holds NUMERIC_FIELDS, validation rules
- **Guard clauses**: Early returns in `getRecommendation`, `fetchPatientContext`

---

## Testing

Run the app to confirm behavior:

```powershell
.\scripts\windows\run_dev.ps1
```

Then exercise the Dashboard, Reports, and Alerts flows.
