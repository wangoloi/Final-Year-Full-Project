import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { WORKSPACE_PATH } from '../constants'
import { apiFetch } from '../api'

/**
 * Model Info page: developer-only view of the active ML model.
 * Access: triple-click the GlucoSense logo in the topbar, or navigate to /model-info.
 * Not shown in the main navigation.
 */
export default function ModelInfo() {
  const [info, setInfo] = useState(null)
  const [importance, setImportance] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const r1 = await apiFetch('/api/model-info')
        if (!r1.ok) {
          const text = await r1.text()
          return setError(text || `Request failed (${r1.status})`)
        }
        const data = await r1.json()
        if (!cancelled) setInfo(data)
        const r2 = await apiFetch('/api/feature-importance')
        if (!cancelled && r2.ok) setImportance(await r2.json())
      } catch (e) {
        if (!cancelled) setError(e.message || 'Failed to load model info')
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (error) return <div className="alert alert-warning" role="alert">{error}</div>
  if (!info) return <div className="loading">Loading model info...</div>

  return (
    <div className="model-info-page">
      <p className="model-info-dev-hint" aria-hidden="true">Developer view — access via triple-click on logo</p>
      <Link to={WORKSPACE_PATH} className="model-info-back">← Back to Dashboard</Link>
      <div className="dashboard-grid">
      <div className="card span-2">
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Model information
          <span className="badge badge-ok" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}>Best model (active)</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
          <div className="metric">
            <div className="metric-label">Model</div>
            <div className="metric-value">{info.model_name}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Metric</div>
            <div className="metric-value">{info.metric_name}: {(info.metric_value * 100).toFixed(2)}%</div>
          </div>
          <div className="metric">
            <div className="metric-label">Features</div>
            <div className="metric-value">{info.n_features}</div>
          </div>
        </div>
        <p><strong>Classes:</strong> {info.classes && info.classes.join(', ')}</p>
        <div className="alert alert-info" style={{ marginTop: '1rem' }}>{info.clinical_disclaimer}</div>
      </div>
      {importance && importance.feature_names && (
        <div className="card span-2">
          <div className="card-title">Feature importance ({importance.source})</div>
          <table>
            <thead>
              <tr><th>Feature</th><th>Importance</th></tr>
            </thead>
            <tbody>
              {importance.feature_names.map((f, i) => (
                <tr key={i}>
                  <td>{f}</td>
                  <td>{importance.importance && importance.importance[i] != null ? Number(importance.importance[i]).toFixed(4) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </div>
    </div>
  )
}
