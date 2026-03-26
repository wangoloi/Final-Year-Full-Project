# GlucoSense — Phase 2 Improvements Implemented

## Summary

Phase 2 improvements from the user-connected design analysis have been implemented. Restart the backend (`uvicorn app:app --reload` or `.\scripts\windows\run_dev.ps1`) to pick up changes.

---

## 1. Level 2 Hypoglycemia (20g carbs)

- **Config**: `level2_hypo_max: 53` mg/dL; `fast_acting_carbs_level2_grams: 20`
- **Schema**: Added `level2_hypo` zone (<54 mg/dL) and `level1_hypo` zone (54–69 mg/dL) to `GLUCOSE_ZONES`
- **recommendation_generator.py**: Uses `get_glucose_zone_cds()` to distinguish Level 2; returns 20g for <54 mg/dL
- **engine.py**: Uses `_hypo_carbs` (20g for level2, 15g for level1) in `recommended_action`, `system_interpretation`, `suggested_action`
- **routes.py**: Alerts use zone-specific carbs (20g for level2_hypo)
- **InsulinManagement.jsx**: FALLBACK_ZONES updated with level2 (20g) and level1 (15g)

---

## 2. IOB Label and Units

- **constants.js**: Added `IOB_MAX_UNITS = 50`, kept `IOB_MAX_ML` for compatibility
- **Dashboard.jsx**: Label changed from "IOB (mL)" to "IOB (units)"; input accepts 0–50 units; converts to mL (÷100) for API
- **engine.py**: Displays IOB as units (×100) in `iob_display`

---

## 3. Primary Action Line

- **Dashboard.jsx**: New "Recommended action" card at top of result section
- **index.css**: `.card-primary-action`, `.card-primary-action--critical`, `.primary-action-text` styles
- Critical cases (e.g. hypo) use red accent; normal cases use blue

---

## 4. Quick-Entry Mode

- **Dashboard.jsx**: "Quick check (glucose only)" checkbox
- When enabled: hides Age, Gender, Food intake, Previous medication, BMI, HbA1c, Weight; uses defaults (age 30, Male, Medium, None)
- Only Glucose and optional IOB/carbs/trend required
- Shows "Last: X mg/dL" under glucose when `recentMetrics.glucose` is available

---

## 5. Actionable Notifications

- **Layout.jsx**: Added "Dashboard" quick link in notifications dropdown (always visible)
- Order: Dashboard → Reports (if download notification) → Alerts

---

## 6. Responsive / Mobile UI

- **index.css**: Media queries for `max-width: 900px` and `600px`
- Form grid collapses to 1 column on small screens
- Primary action text scales down
- Buttons use min-height 44px for touch targets

---

## Files Modified

| File | Changes |
|------|---------|
| `src/insulin_system/recommendation/recommendation_generator.py` | Level 2 hypo carbs, `get_glucose_zone_cds` |
| `src/insulin_system/api/engine.py` | `_hypo_carbs`, `_cds_cat`, IOB display in units |
| `src/insulin_system/config/schema.py` | `level2_hypo` / `level1_hypo` zones, `FAST_ACTING_CARBS_LEVEL2_GRAMS` |
| `src/insulin_system/api/routes.py` | Zone-specific carbs in alerts |
| `frontend/src/constants.js` | `IOB_MAX_UNITS` |
| `frontend/src/pages/Dashboard.jsx` | IOB units, quick entry, primary action card |
| `frontend/src/pages/InsulinManagement.jsx` | Level 2/1 fallback zones |
| `frontend/src/components/Layout.jsx` | Dashboard quick link |
| `frontend/src/index.css` | Primary action, responsive styles |

---

## How to Run

```powershell
.\scripts\windows\run_dev.ps1
```

Or separately:
```powershell
# Terminal 1
uvicorn app:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

**Important**: Restart the backend after pulling these changes so Level 2 hypo (20g) and IOB display work correctly.
