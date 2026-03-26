import { useState, useEffect } from 'react'
import { GLUCOSE_MIN, GLUCOSE_MAX, ANTICIPATED_CARBS_MAX_G } from '../constants'
import { apiFetch } from '../api'

const API = '/api'

const SEVERITY_STYLES = {
  critical: { bg: 'rgba(198, 40, 40, 0.12)', borderColor: '#c62828' },
  warning: { bg: 'rgba(239, 108, 0, 0.12)', borderColor: '#ef6c00' },
  caution: { bg: 'rgba(255, 193, 7, 0.18)', borderColor: '#ffc107' },
  normal: { bg: 'rgba(76, 175, 80, 0.12)', borderColor: '#4caf50' },
}

// Simple plain-language explanations for each zone (what the reading means in practice)
const ZONE_EXPLANATIONS = {
  hypo: 'Your blood sugar is too low. Do not take insulin. Treat with fast-acting carbs first and recheck in 15 minutes.',
  low_normal: 'Your blood sugar is on the lower side of normal. Dose only for the food you eat; reduce the meal bolus to avoid going lower.',
  target: 'Your blood sugar is in a good range. Use your usual insulin-to-carb ratio for meals; no correction dose needed.',
  mild_hyper: 'Your blood sugar is slightly high. A small correction may help, but only if you have little active insulin on board.',
  moderate_high: 'Your blood sugar is elevated. Consider a correction dose and check for hydration, stress, or missed insulin.',
  severe_high: 'Your blood sugar is very high. Treat with a correction dose and check for ketones if it stays high for more than 2 hours.',
}

// Fallback zones (match backend) so lookup works even before API loads
const FALLBACK_ZONES = [
  { id: 'level2_hypo', min_mg_dl: null, max_mg_dl: 53, label: '<54 mg/dL', interpretation: 'Level 2 Hypoglycemia', action: 'Stop. Suspend all insulin logic. Consume 20g fast-acting carbs. Recheck in 15 min.', severity: 'critical' },
  { id: 'hypo', min_mg_dl: 54, max_mg_dl: 69, label: '54–69 mg/dL', interpretation: 'Level 1 Hypoglycemia', action: 'Stop. Suspend all insulin logic. Consume 15g fast-acting carbs. Recheck in 15 min.', severity: 'critical' },
  { id: 'low_normal', min_mg_dl: 70, max_mg_dl: 90, label: '70 – 90', interpretation: 'Low-Normal', action: 'Dose for food only. Subtract from the meal bolus to prevent a dip.', severity: 'caution' },
  { id: 'target', min_mg_dl: 90, max_mg_dl: 130, label: '90 – 130', interpretation: 'Target Range', action: 'Standard Dose. Apply Insulin-to-Carb Ratio only. No correction needed.', severity: 'normal' },
  { id: 'mild_hyper', min_mg_dl: 131, max_mg_dl: 180, label: '131 – 180', interpretation: 'Mild Hyperglycemia', action: 'Apply Correction Factor (ISF) for the excess, but only if IOB is low.', severity: 'caution' },
  { id: 'moderate_high', min_mg_dl: 181, max_mg_dl: 250, label: '181 – 250', interpretation: 'Moderate High', action: 'Add Correction Dose. Prompt user to check for hydration/stress factors.', severity: 'warning' },
  { id: 'severe_high', min_mg_dl: 251, max_mg_dl: null, label: 'Above 250', interpretation: 'Severe High', action: 'Add Correction Dose. Urgent Alert: Check for Ketones if BG remains high for >2 hours.', severity: 'critical' },
]

export default function InsulinManagement() {
  const [zones, setZones] = useState([])
  const [lookupGlucose, setLookupGlucose] = useState('')
  const [interpretResult, setInterpretResult] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiFetch(`${API}/glucose-zones`)
      .then((r) => (r.ok ? r.json() : { zones: [] }))
      .then((d) => setZones(d.zones || []))
      .catch(() => setZones([]))
  }, [])

  /** Find zone for glucose using same logic as backend (works with zones or fallback). */
  const findZoneForGlucose = (glucoseVal, zonesToUse) => {
    const gl = Number(glucoseVal)
    if (Number.isNaN(gl)) return null
    const list = zonesToUse?.length > 0 ? zonesToUse : FALLBACK_ZONES
    for (const z of list) {
      const min = z.min_mg_dl
      const max = z.max_mg_dl
      if (min != null && gl < min) continue
      if (max != null && gl > max) continue
      return z
    }
    return null
  }

  const handleLookup = () => {
    const val = parseFloat(lookupGlucose)
    if (Number.isNaN(val) || val < 0) {
      setInterpretResult({ glucose: lookupGlucose, zone: null, message: 'Enter a valid glucose value (mg/dL).' })
      return
    }
    setLoading(true)
    setInterpretResult(null)
    // Client-side lookup using zones (from API or fallback) - reliable, no extra API call
    const zone = findZoneForGlucose(val, zones)
    setInterpretResult({ glucose: val, zone, message: zone ? null : 'No zone found for this value.' })
    setLoading(false)
  }

  return (
    <div className="page-management">
      <div className="page-header">
        <h1 className="page-title">Glucose Interpretation & Dosage Chart</h1>
        <p className="page-description">
          Standard reference for how glucose figures influence insulin action. Zones trigger specific alerts in the system.
        </p>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h2 className="card-heading">Quick lookup</h2>
        <p className="card-description">Enter a glucose value to see which zone applies and the recommended action.</p>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <label className="form-field" style={{ marginBottom: 0, minWidth: 160 }}>
            <span className="form-label">Glucose (mg/dL)</span>
            <input
              type="number"
              min={GLUCOSE_MIN}
              max={GLUCOSE_MAX}
              step="1"
              value={lookupGlucose}
              onChange={(e) => setLookupGlucose(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
              placeholder="e.g. 120"
              className="form-input"
            />
          </label>
          <button type="button" className="btn btn-primary" onClick={handleLookup} disabled={loading}>
            {loading ? 'Looking up…' : 'Interpret'}
          </button>
        </div>
        {interpretResult && (
          <div
            className="zone-interpret-result"
            style={{
              marginTop: '1rem',
              padding: '1rem',
              borderRadius: 8,
              background: interpretResult.zone
                ? SEVERITY_STYLES[interpretResult.zone.severity]?.bg || 'var(--bg-alt)'
                : 'var(--bg-alt)',
              border: interpretResult.zone
                ? `2px solid ${SEVERITY_STYLES[interpretResult.zone.severity]?.borderColor || 'var(--border)'}`
                : '1px solid var(--border)',
            }}
          >
            {interpretResult.zone ? (
              <>
                <strong>{interpretResult.glucose} mg/dL</strong> — {interpretResult.zone.interpretation}
                <p style={{ margin: '0.5rem 0 0', fontSize: '0.95rem', fontWeight: 500 }}>
                  {ZONE_EXPLANATIONS[interpretResult.zone.id] || interpretResult.zone.action}
                </p>
                <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  {interpretResult.zone.action}
                </p>
              </>
            ) : (
              <span>{interpretResult.message || 'No zone found.'}</span>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="card-heading">Glucose zones reference</h2>
        <p className="card-description">
          These zones are hardcoded into the system and influence recommendations and alerts.
        </p>
        <div className="zones-table-wrapper" style={{ overflowX: 'auto' }}>
          <table className="zones-table" role="grid" aria-label="Glucose interpretation zones">
            <thead>
              <tr>
                <th>Glucose Range (mg/dL)</th>
                <th>Clinical Interpretation</th>
                <th>System Action / Logic Influence</th>
              </tr>
            </thead>
            <tbody>
              {(zones.length > 0 ? zones : FALLBACK_ZONES).map((z) => (
                <tr
                  key={z.id}
                  data-severity={z.severity}
                  style={{
                    background: SEVERITY_STYLES[z.severity]?.bg || 'transparent',
                    borderLeft: SEVERITY_STYLES[z.severity]?.borderColor ? `4px solid ${SEVERITY_STYLES[z.severity].borderColor}` : undefined,
                  }}
                >
                  <td>
                    <strong>{z.label}</strong>
                  </td>
                  <td>{z.interpretation}</td>
                  <td>{z.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}
