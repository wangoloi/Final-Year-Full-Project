# Uganda Clinical Guideline 2023 – Type 1 Diabetes

GlucoSense integrates the **Uganda Clinical Guideline 2023** for Type 1 Diabetes management. All rule-based logic follows these guidelines.

---

## Daily Insulin Dose (SC)

| Population | Dose Range |
|------------|------------|
| Adults & children ≥5 years | 0.6 – 1.5 IU/kg/day |
| Children <5 years | 0.5 IU/kg/day; **refer to paediatrician** |

---

## Insulin Types & Protocols

| Type | Example | Protocol | Timing | Onset | Peak | Duration |
|------|---------|----------|--------|-------|------|----------|
| Short acting (regular) | Actrapid | 3× daily | 30 min before meals | 30 min | 2–5 h | 5–8 h |
| Rapid acting | Aspart | 3× daily | 10–15 min before meals | 10–20 min | 45 min | 3–5 h |
| Intermediate (NPH) | Insulatard | 1–2× daily | Evening ± morning | 1–3 h | 6–12 h | 16–24 h |
| Biphasic | Mixtard 30/70 | 1–2× daily | 30 min before meals | 2 h | 2–12 h | 16–24 h |

---

## Preferred Regimens

### 1. Basal–bolus (preferred)

- **Bolus**: Pre-meal short acting (Actrapid) or rapid acting (Aspart)
- **Basal**: Evening intermediate (Insulatard) or long acting (Glargine)
- **Evening dose**: 40–50% of total daily dose

### 2. Twice-daily premixed

- **Mixtard**: 2/3 of total dose in morning, 1/3 in evening (30 min before meals)
- **Biphasic Aspart**: 2/3 morning, 1/3 evening (10–15 min before meals)

---

## Configuration

- **Clinical thresholds**: `config/clinical_thresholds.json`
- **Uganda guidelines**: `config/uganda_t1d_guidelines.json`

Edit these JSON files to adjust thresholds without changing code.
