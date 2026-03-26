import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

const API = '/api'

export default function Records() {
  const [data, setData] = useState({ records: [], count: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await apiFetch(`${API}/records?limit=100`)
        if (!res.ok) throw new Error(await res.text())
        const json = await res.json()
        if (!cancelled) setData(json)
      } catch (e) {
        if (!cancelled) setError(e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) return <div className="loading">Loading records...</div>
  if (error) return <div className="alert alert-warning">{error}</div>

  const records = data.records || []

  return (
    <div className="dashboard-grid">
      <div className="card span-2">
        <div className="card-title">Stored records ({records.length})</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Prediction and recommendation history from the database. Each row is one API call.
        </p>
        {records.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No records yet. Use the Dashboard to get recommendations; they will be saved here.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Endpoint</th>
                  <th>Predicted</th>
                  <th>Confidence</th>
                  <th>High risk</th>
                  <th>Request ID</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id}>
                    <td>{r.created_at ? new Date(r.created_at).toLocaleString() : '-'}</td>
                    <td>{r.endpoint}</td>
                    <td>{r.predicted_class || '-'}</td>
                    <td>{r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : '-'}</td>
                    <td>{r.is_high_risk ? 'Yes' : 'No'}</td>
                    <td style={{ fontSize: '0.8rem' }}>{r.request_id ? r.request_id.slice(0, 8) + '...' : '-'}</td>
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
