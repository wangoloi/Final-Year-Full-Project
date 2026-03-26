import { useState } from 'react'
import { apiFetch } from '../api'

const API = '/api'

const numericFields = [
  { key: 'age', label: 'Age (years)' },
  { key: 'glucose_level', label: 'Glucose level (mg/dL)' },
  { key: 'physical_activity', label: 'Physical activity' },
  { key: 'BMI', label: 'BMI' },
  { key: 'HbA1c', label: 'HbA1c (%)' },
  { key: 'weight', label: 'Weight (kg)' },
  { key: 'insulin_sensitivity', label: 'Insulin sensitivity' },
  { key: 'sleep_hours', label: 'Sleep (hours)' },
  { key: 'creatinine', label: 'Creatinine (mg/dL)' },
]
const categoricalFields = [
  { key: 'gender', label: 'Gender' },
  { key: 'family_history', label: 'Family history' },
  { key: 'food_intake', label: 'Food intake' },
  { key: 'previous_medications', label: 'Previous medications' },
]

const initialForm = () => {
  const o = { patient_id: '' }
  numericFields.forEach(({ key }) => { o[key] = '' })
  categoricalFields.forEach(({ key }) => { o[key] = '' })
  return o
}

export default function Recommendation() {
  const [form, setForm] = useState(initialForm())
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setError(null)
  }

  const buildBody = () => {
    const body = {}
    if (form.patient_id) body.patient_id = form.patient_id
    numericFields.forEach(({ key }) => {
      if (form[key] !== '' && form[key] != null) body[key] = Number(form[key])
    })
    categoricalFields.forEach(({ key }) => {
      if (form[key] !== '' && form[key] != null) body[key] = String(form[key])
    })
    return body
  }

  const getRecommendation = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${API}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildBody()),
      })
      if (!res.ok) {
        const t = await res.text()
        throw new Error(t || res.statusText)
      }
      const data = await res.json()
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const getPrediction = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await apiFetch(`${API}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildBody()),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setResult({ ...data, recommendation_summary: data.predicted_class, recommendation_detail: '', dosage_action: '-', dosage_magnitude: '-', is_high_risk: false, explanation_drivers: [], alternative_scenarios: [] })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Patient input</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Enter available patient data. Missing fields may be imputed by the system. At least a few numeric values improve prediction.
      </p>
      <div className="card">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
          {numericFields.map(({ key, label }) => (
            <label key={key}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{label}</span>
              <input
                type="number"
                step="any"
                value={form[key] ?? ''}
                onChange={(e) => handleChange(key, e.target.value)}
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}
              />
            </label>
          ))}
          {categoricalFields.map(({ key, label }) => (
            <label key={key}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{label}</span>
              <input
                type="text"
                value={form[key] ?? ''}
                onChange={(e) => handleChange(key, e.target.value)}
                placeholder="e.g. Yes / No"
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}
              />
            </label>
          ))}
        </div>
        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button onClick={getPrediction} disabled={loading} style={{ padding: '0.6rem 1.2rem', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontWeight: 600 }}>
            {loading ? 'Loading...' : 'Get prediction'}
          </button>
          <button onClick={getRecommendation} disabled={loading} style={{ padding: '0.6rem 1.2rem', background: 'var(--primary-dark)', color: 'white', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontWeight: 600 }}>
            {loading ? 'Loading...' : 'Get recommendation'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-warning">{error}</div>}

      {result && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h2>Output</h2>
          <div className="grid-3">
            <div className="metric">
              <div className="metric-label">Predicted category</div>
              <div className="metric-value">{result.predicted_class}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Confidence</div>
              <div className="metric-value">{(result.confidence * 100).toFixed(0)}%</div>
            </div>
            <div className="metric">
              <div className="metric-label">Dosage suggestion</div>
              <div className="metric-value">{result.dosage_action} ({result.dosage_magnitude})</div>
            </div>
          </div>
          {result.is_high_risk && (
            <div className="alert alert-warning" style={{ marginTop: '1rem' }}>
              <strong>Flag for clinician review:</strong> {result.high_risk_reason}
            </div>
          )}
          <h3 style={{ fontSize: '1rem', marginTop: '1.25rem' }}>Recommendation</h3>
          <p>{result.recommendation_summary}</p>
          <p style={{ color: 'var(--text-muted)' }}>{result.recommendation_detail}</p>
          {result.explanation_drivers && result.explanation_drivers.length > 0 && (
            <>
              <h3 style={{ fontSize: '1rem', marginTop: '1.25rem' }}>Key factors</h3>
              <ul style={{ paddingLeft: '1.25rem' }}>
                {result.explanation_drivers.slice(0, 8).map((d, i) => (
                  <li key={i}>{d.clinical_sentence || `${d.feature}: ${d.value}`}</li>
                ))}
              </ul>
            </>
          )}
          {result.alternative_scenarios && result.alternative_scenarios.length > 0 && (
            <>
              <h3 style={{ fontSize: '1rem', marginTop: '1.25rem' }}>Alternative scenarios</h3>
              <ul style={{ paddingLeft: '1.25rem' }}>
                {result.alternative_scenarios.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          )}
          <div className="alert alert-info" style={{ marginTop: '1.5rem' }}>
            {result.clinical_disclaimer}
          </div>
        </div>
      )}
    </div>
  )
}
