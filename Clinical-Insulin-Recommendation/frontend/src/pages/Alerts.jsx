import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiAlertTriangle, FiCheck, FiCheckCircle, FiRefreshCw, FiExternalLink } from 'react-icons/fi'
import { useClinical } from '../context/ClinicalContext'
import * as clinicalApi from '../services/clinicalApi'
import { WORKSPACE_PATH } from '../constants'

function formatTime(created_at) {
  if (!created_at) return ''
  try {
    const d = new Date(created_at)
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch (_) {
    return String(created_at).slice(0, 16)
  }
}

function getAlertAction(alert) {
  const title = (alert?.title || '').toLowerCase()
  const text = (alert?.text || '').toLowerCase()
  if (title.includes('recommendation') || text.includes('recommendation') || text.includes('review')) {
    return { label: 'Go to Dashboard', path: WORKSPACE_PATH }
  }
  if (title.includes('hypoglycemia') || title.includes('hyperglycemia') || text.includes('glucose')) {
    return { label: 'Go to Dashboard', path: WORKSPACE_PATH }
  }
  return { label: 'Go to Reports', path: `${WORKSPACE_PATH}/reports` }
}

export default function Alerts() {
  const navigate = useNavigate()
  const { refreshFromApi } = useClinical()
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showResolved, setShowResolved] = useState(false)
  const [filterSeverity, setFilterSeverity] = useState('all')
  const [resolvingId, setResolvingId] = useState(null)
  const [resolvingAll, setResolvingAll] = useState(false)

  const fetchAlerts = useCallback(async () => {
    try {
      const items = await clinicalApi.fetchAlerts(100, !showResolved)
      setAlerts(items)
    } catch (_) {
      setAlerts([])
    } finally {
      setLoading(false)
    }
  }, [showResolved])

  useEffect(() => {
    setLoading(true)
    fetchAlerts()
  }, [fetchAlerts])

  const handleResolve = async (id) => {
    setResolvingId(id)
    try {
      const ok = await clinicalApi.resolveAlert(id)
      if (ok) {
        await fetchAlerts()
        refreshFromApi?.()
      }
    } finally {
      setResolvingId(null)
    }
  }

  const handleResolveAll = async () => {
    setResolvingAll(true)
    try {
      await clinicalApi.resolveAllAlerts()
      await fetchAlerts()
      refreshFromApi?.()
    } finally {
      setResolvingAll(false)
    }
  }

  const filtered = alerts.filter((a) => {
    if (filterSeverity === 'all') return true
    return (a.severity || 'warning') === filterSeverity
  })

  const unresolvedCount = alerts.filter((a) => !a.resolved).length
  const criticalCount = alerts.filter((a) => a.severity === 'critical').length
  const warningCount = alerts.filter((a) => a.severity !== 'critical').length

  if (loading) return <div className="loading">Loading alerts…</div>

  return (
    <div className="page-alerts">
      <div className="page-header">
        <h1 className="page-title">Alerts</h1>
        <p className="page-description">
          Critical conditions from glucose readings and recommendations. Resolve alerts after taking action.
        </p>
      </div>

      <div className="alerts-summary-cards">
        <div className="alerts-summary-card alerts-summary--unresolved">
          <span className="alerts-summary-value">{unresolvedCount}</span>
          <span className="alerts-summary-label">Unresolved</span>
        </div>
        <div className="alerts-summary-card alerts-summary--critical">
          <span className="alerts-summary-value">{criticalCount}</span>
          <span className="alerts-summary-label">Critical</span>
        </div>
        <div className="alerts-summary-card alerts-summary--warning">
          <span className="alerts-summary-value">{warningCount}</span>
          <span className="alerts-summary-label">Warning</span>
        </div>
      </div>

      <div className="card">
        <div className="alerts-toolbar">
          <div className="alerts-filters">
            <label className="alerts-toggle">
              <input
                type="checkbox"
                checked={showResolved}
                onChange={(e) => setShowResolved(e.target.checked)}
              />
              Show resolved
            </label>
            <label className="alerts-filter-severity">
              <span className="alerts-filter-label">Severity</span>
              <select
                className="form-select alerts-select"
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
                aria-label="Filter by severity"
              >
                <option value="all">All</option>
                <option value="critical">Critical only</option>
                <option value="warning">Warning only</option>
              </select>
            </label>
          </div>
          <div className="alerts-actions">
            <button
              type="button"
              className="btn btn-text btn-sm"
              onClick={fetchAlerts}
              disabled={loading}
              title="Refresh"
            >
              <FiRefreshCw size={16} /> Refresh
            </button>
            {unresolvedCount > 0 && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleResolveAll}
                disabled={resolvingAll}
              >
                {resolvingAll ? 'Resolving…' : (
                  <>
                    <FiCheckCircle size={16} /> Resolve all
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="alerts-empty-state">
            <FiAlertTriangle size={48} className="alerts-empty-icon" />
            <p className="alerts-empty-title">No alerts to show</p>
            <p className="alerts-empty-description">
              {showResolved
                ? 'No resolved alerts. Alerts appear when glucose is critically low or high, or when a recommendation is flagged for review.'
                : 'Alerts are generated from the Dashboard when glucose readings or recommendations require attention.'}
            </p>
          </div>
        ) : (
          <ul className="alerts-list" role="list">
            {filtered.map((a) => {
              const severity = a.severity || 'warning'
              const action = getAlertAction(a)
              const isResolved = !!a.resolved
              return (
                <li
                  key={a.id}
                  className={`alerts-item alerts-item--${severity} ${isResolved ? 'alerts-item--resolved' : ''}`}
                  role="alert"
                >
                  <span className="alerts-badge">
                    {severity === 'critical' ? 'Critical' : 'Warning'}
                  </span>
                  <div className="alerts-content">
                    <strong className="alerts-title">{a.title}</strong>
                    <p className="alerts-text">{a.text}</p>
                    <div className="alerts-meta">
                      <span className="alerts-time">{formatTime(a.created_at)}</span>
                      {!isResolved && (
                        <div className="alerts-item-actions">
                          <button
                            type="button"
                            className="btn btn-text btn-sm alerts-action-link"
                            onClick={() => navigate(action.path)}
                          >
                            <FiExternalLink size={14} /> {action.label}
                          </button>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm alerts-resolve-btn"
                            onClick={() => handleResolve(a.id)}
                            disabled={resolvingId === a.id}
                            title="Mark as resolved"
                          >
                            {resolvingId === a.id ? (
                              'Resolving…'
                            ) : (
                              <>
                                <FiCheck size={14} /> Mark resolved
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
