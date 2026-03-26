# CDS Safety Engine for Type 1 Diabetes

GlucoSense implements a Clinical Decision Support (CDS) Safety Engine aligned with standard T1D management guidelines.

---

## Glucose Categorization

| Category | Range | Severity |
|----------|-------|----------|
| Level 2 Hypoglycemia | <54 mg/dL | Critical |
| Level 1 Hypoglycemia | 54–69 mg/dL | Critical |
| Target Range | 70–180 mg/dL | Normal |
| Hyperglycemia | 181–250 mg/dL | Warning |
| Critical Alert | >250 mg/dL or high ketones | Critical |

---

## Safety Checks (Hard Stops)

1. **Glucose <70 mg/dL**: REJECT any insulin recommendation. Trigger alert. Suggest 15g fast-acting carbs.
2. **Adjustment >> typical**: If suggested dose >2× typical correction (from 7-day TDD), flag `high_uncertainty`.
3. **CGM sensor error**: Set confidence to LOW (max 0.5). Require manual finger-stick. Add `cgm_error` risk flag.
4. **High ketones**: Flag `high_ketones`. Add critical alert to suggested action.

---

## Input Fields (POST /recommend)

| Field | Type | Description |
|-------|------|-------------|
| `ketone_level` | string | none, trace, small, moderate, large, high |
| `cgm_sensor_error` | boolean | True if CGM reports sensor error |
| `typical_daily_insulin` | float | 7-day average TDD (units) for HIGH UNCERTAINTY check |

---

## Output Format (CDS Structured)

```json
{
  "status": "ok",
  "category": "target_range",
  "suggested_action": "The system suggests Maintain current dose. No change. Draft Recommendation.",
  "rationale": "The system suggests Your blood sugar is in a good range. Use your usual dose for food; no correction needed.",
  "confidence_level": 0.85,
  "risk_flags": [],
  "requires_urgent_validation": false
}
```

When `confidence_level < 0.8`: `requires_urgent_validation: true` and rationale includes "Requires Urgent Clinician Validation."

When rejected (glucose <70):

```json
{
  "status": "rejected",
  "category": "level1_hypoglycemia",
  "suggested_action": "REJECTED: Do not administer insulin. Consume 15g fast-acting carbs. Manual finger-stick check recommended.",
  "risk_flags": ["hypoglycemia_alert"]
}
```

---

## Risk Flags

| Flag | Meaning |
|------|---------|
| `hypoglycemia_alert` | Glucose <70; insulin rejected |
| `high_uncertainty` | Low confidence or adjustment >> typical |
| `cgm_error` | CGM sensor error; finger-stick required |
| `high_ketones` | High ketone levels reported |

---

## Language Constraints

All recommendations use "The system suggests..." phrasing. The clinician remains the final decision-maker.
