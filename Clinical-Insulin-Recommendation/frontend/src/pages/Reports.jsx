import { useState, useEffect, useCallback, Fragment } from 'react'
import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { useClinical } from '../context/ClinicalContext'
import { apiFetch } from '../api'

const API = '/api'
const REPORTS_DOWNLOAD_TYPE = 'reports_download'

const HOURS_12_MS = 12 * 60 * 60 * 1000

const TIME_RANGE_OPTIONS = [
  { value: '12h', label: 'Last 12 hours' },
  { value: 'all', label: 'All sessions' },
]

const ENDPOINT_OPTIONS = [
  { value: '', label: 'All types' },
  { value: 'recommend', label: 'Recommendation' },
  { value: 'predict', label: 'Prediction' },
  { value: 'explain', label: 'Explanation' },
]

const INPUT_LABELS = {
  glucose_level: 'Glucose (mg/dL)',
  iob: 'Insulin on board (mL)',
  anticipated_carbs: 'Anticipated carbs (g)',
  glucose_trend: 'Glucose trend',
  age: 'Age',
  food_intake: 'Food intake',
  physical_activity: 'Activity (min)',
  weight: 'Weight (kg)',
  BMI: 'BMI',
  HbA1c: 'HbA1c (%)',
}

function formatType(endpoint) {
  const o = ENDPOINT_OPTIONS.find((e) => e.value === endpoint)
  return o ? o.label : (endpoint || '—')
}

function formatOutcome(predictedClass) {
  if (predictedClass == null) return '—'
  return String(predictedClass).replace(/_/g, ' ')
}

function formatInputValue(key, value) {
  if (value == null) return '—'
  if (key === 'glucose_trend') return String(value).replace(/_/g, ' ')
  return String(value)
}

function getInputSummaryDisplay(input) {
  if (!input || typeof input !== 'object') return []
  if ('n_fields' in input && Object.keys(input).length === 1) return []
  return Object.entries(input)
    .filter(([k]) => k !== 'n_fields')
    .map(([k, v]) => ({ label: INPUT_LABELS[k] || k, value: formatInputValue(k, v) }))
}

const STORAGE_KEY = 'glucosense_reports_downloaded_dates'

/** Get YYYY-MM-DD (local) from record. */
function getRecordDate(record) {
  if (!record?.created_at) return null
  const d = new Date(record.created_at)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Get unique dates (YYYY-MM-DD) from records, newest first. */
function getDatesWithRecords(records) {
  const set = new Set()
  records.forEach((r) => {
    const d = getRecordDate(r)
    if (d) set.add(d)
  })
  return [...set].sort().reverse()
}

/** Filter records to those within the last 12 hours. */
function filterLast12Hours(records) {
  const cutoff = Date.now() - HOURS_12_MS
  return records.filter((r) => {
    if (!r?.created_at) return false
    const ts = new Date(r.created_at).getTime()
    return ts >= cutoff
  })
}

function getDownloadedDates() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function markDatesAsDownloaded(dates) {
  const existing = new Set(getDownloadedDates())
  dates.forEach((d) => existing.add(d))
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...existing]))
}

/** Trigger file download to local storage. */
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** Export filtered records as CSV (person-centric + outcome). Marks dates as downloaded. */
function exportToCsv(records, onDownloaded) {
  const headers = ['Date & time', 'Glucose', 'IOB', 'Carbs', 'Trend', 'Type', 'Outcome', 'Review', 'Request ID']
  const rows = records.map((r) => {
    const in_ = r.input_summary || {}
    return [
      r.created_at ? new Date(r.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '',
      in_.glucose_level ?? '',
      in_.iob ?? '',
      in_.anticipated_carbs ?? '',
      in_.glucose_trend ? String(in_.glucose_trend).replace(/_/g, ' ') : '',
      formatType(r.endpoint),
      formatOutcome(r.predicted_class),
      r.is_high_risk ? 'Review' : 'OK',
      r.request_id || '',
    ]
  })
  const escape = (v) => (v == null ? '' : String(v).includes(',') || String(v).includes('"') ? `"${String(v).replace(/"/g, '""')}"` : v)
  const csv = [headers.map(escape).join(','), ...rows.map((row) => row.map(escape).join(','))].join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const dates = getDatesWithRecords(records)
  const ts = dates.length === 1 ? dates[0] : new Date().toISOString().slice(0, 10)
  downloadBlob(blob, `glucosense-reports-${ts}.csv`)
  if (dates.length > 0) {
    markDatesAsDownloaded(dates)
    onDownloaded?.()
  }
}

/** Export filtered records as PDF (person-centric + outcome). Marks dates as downloaded. */
function exportToPdf(records, onDownloaded) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  doc.setFontSize(16)
  doc.text('GlucoSense Reports', 14, 20)
  doc.setFontSize(10)
  doc.text(`Generated ${new Date().toLocaleString()}`, 14, 28)
  doc.setFontSize(9)

  const headers = [['Date & time', 'Glucose', 'IOB', 'Carbs', 'Trend', 'Type', 'Outcome', 'Review']]
  const body = records.map((r) => {
    const in_ = r.input_summary || {}
    return [
      r.created_at ? new Date(r.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—',
      in_.glucose_level ?? '—',
      in_.iob ?? '—',
      in_.anticipated_carbs ?? '—',
      in_.glucose_trend ? String(in_.glucose_trend).replace(/_/g, ' ') : '—',
      formatType(r.endpoint),
      formatOutcome(r.predicted_class),
      r.is_high_risk ? 'Review' : 'OK',
    ]
  })

  autoTable(doc, {
    head: headers,
    body,
    startY: 35,
    theme: 'grid',
    styles: { fontSize: 8 },
    headStyles: { fillColor: [21, 101, 192] },
  })

  const dates = getDatesWithRecords(records)
  const ts = dates.length === 1 ? dates[0] : new Date().toISOString().slice(0, 10)
  doc.save(`glucosense-reports-${ts}.pdf`)
  if (dates.length > 0) {
    markDatesAsDownloaded(dates)
    onDownloaded?.()
  }
}

function formatDateLabel(dateStr) {
  const d = new Date(dateStr + 'T12:00:00')
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}

export default function Reports() {
  const { refreshFromApi } = useClinical()
  const [data, setData] = useState({ records: [], count: 0 })
  const [patientCtx, setPatientCtx] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterType, setFilterType] = useState('')
  const [filterDate, setFilterDate] = useState('all')
  const [timeRange, setTimeRange] = useState('12h')
  const [expandedId, setExpandedId] = useState(null)
  const [, setDownloadedVersion] = useState(0)
  const [deletingId, setDeletingId] = useState(null)

  const loadReports = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const [recRes, ctxRes] = await Promise.all([
        apiFetch(`${API}/records?limit=100`),
        apiFetch(`${API}/patient-context`),
      ])
      if (!recRes.ok) throw new Error(await recRes.text())
      const json = await recRes.json()
      setData(json)
      if (ctxRes.ok) {
        const ctx = await ctxRes.json()
        setPatientCtx(ctx)
      }
    } catch (e) {
      if (!silent) setError(e.message)
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadReports(false)
  }, [loadReports])

  const handleDeleteRecord = async (recordId) => {
    if (!window.confirm('Delete this report? This cannot be undone.')) return
    setDeletingId(recordId)
    try {
      const res = await apiFetch(`${API}/records/${recordId}`, { method: 'DELETE' })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        window.alert(body.detail || body.message || 'Could not delete report.')
        return
      }
      if (expandedId === recordId) setExpandedId(null)
      await loadReports(true)
      refreshFromApi?.()
    } catch (e) {
      window.alert(e.message || 'Delete failed.')
    } finally {
      setDeletingId(null)
    }
  }

  const allRecords = data.records || []
  const records = timeRange === '12h' ? filterLast12Hours(allRecords) : allRecords
  const datesWithRecords = getDatesWithRecords(records)
  const downloadedDates = getDownloadedDates()
  const undownloadedDates = datesWithRecords.filter((d) => !downloadedDates.includes(d))

  const byType = filterType ? records.filter((r) => r.endpoint === filterType) : records
  const filtered = filterDate === 'all'
    ? byType
    : byType.filter((r) => getRecordDate(r) === filterDate)

  const handleDownloaded = () => setDownloadedVersion((v) => v + 1)

  useEffect(() => {
    if (loading) return
    const syncNotification = async () => {
      try {
        if (undownloadedDates.length > 0) {
          const label = undownloadedDates.length === 1
            ? formatDateLabel(undownloadedDates[0])
            : `${undownloadedDates.length} days`
          await apiFetch(`${API}/notifications`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: `Reports from ${label} ready to download. Go to Reports to download before the next session.`,
              type: REPORTS_DOWNLOAD_TYPE,
            }),
          })
        } else {
          await apiFetch(`${API}/notifications/by-type/${REPORTS_DOWNLOAD_TYPE}`, { method: 'DELETE' })
        }
        refreshFromApi?.()
      } catch (_) {}
    }
    syncNotification()
  }, [loading, undownloadedDates.join(','), refreshFromApi])

  if (loading) return <div className="loading">Loading session history…</div>
  if (error) return <div className="alert alert-warning">{error}</div>

  return (
    <div className="page-reports">
      <div className="page-header">
        <h1 className="page-title">Reports</h1>
        <p className="page-description">Assessment history. By default shows the last 12 hours. Switch to All sessions to see older records.</p>
      </div>
      {patientCtx && (patientCtx.name || patientCtx.condition || patientCtx.glucose != null) && (
        <div className="card reports-patient-card">
          <h2 className="card-heading">Assessed person</h2>
          <div className="reports-patient-summary">
            {patientCtx.name && <span className="reports-patient-name">{patientCtx.name}</span>}
            {patientCtx.condition && <span className="reports-patient-condition">{patientCtx.condition}</span>}
            <div className="reports-patient-metrics">
              {patientCtx.glucose != null && <span>Last glucose: <strong>{patientCtx.glucose} mg/dL</strong></span>}
              {patientCtx.carbohydrates != null && <span>Carbs: <strong>{patientCtx.carbohydrates} g</strong></span>}
              {patientCtx.activity_minutes != null && <span>Activity: <strong>{patientCtx.activity_minutes} min</strong></span>}
            </div>
          </div>
        </div>
      )}
      <div className="card">
        <div className="reports-toolbar">
          <h2 className="card-heading">
            {timeRange === '12h' ? 'Last 12 hours' : filterDate === 'all' ? 'All sessions' : formatDateLabel(filterDate)} ({filtered.length} records)
          </h2>
          <div className="reports-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => exportToCsv(filtered, handleDownloaded)}
              disabled={filtered.length === 0}
              title="Download as CSV"
            >
              Download CSV
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => exportToPdf(filtered, handleDownloaded)}
              disabled={filtered.length === 0}
              title="Download as PDF"
            >
              Download PDF
            </button>
            <label className="reports-filter">
              <span className="reports-filter-label">Time range</span>
              <select
                className="form-select reports-filter-select"
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                aria-label="Filter by time range"
              >
                {TIME_RANGE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
            <label className="reports-filter" title={timeRange === '12h' ? 'Session filter available when viewing All sessions' : undefined}>
              <span className="reports-filter-label">Session</span>
              <select
                className="form-select reports-filter-select"
                value={filterDate}
                onChange={(e) => setFilterDate(e.target.value)}
                aria-label="Filter by date"
                disabled={timeRange === '12h'}
              >
                <option value="all">All days</option>
                {datesWithRecords.map((d) => (
                  <option key={d} value={d}>{formatDateLabel(d)}</option>
                ))}
              </select>
            </label>
            <label className="reports-filter">
              <span className="reports-filter-label">Type</span>
              <select
                className="form-select reports-filter-select"
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                aria-label="Filter by type"
              >
                {ENDPOINT_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <p className="card-description">
          {timeRange === '12h'
            ? 'Sessions from the last 12 hours. Switch to All sessions to view or download older records.'
            : 'Assessment context and recommendation for each record.'}
        </p>
        {filtered.length === 0 ? (
          <div className="reports-empty">
            <p className="chart-empty-title">No sessions yet</p>
            <p className="chart-empty-description">Recommendations from the Dashboard appear here after you enter assessment data and click Get recommendation.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table reports-table">
              <thead>
                <tr>
                  <th>Date & time</th>
                  <th>Glucose</th>
                  <th>IOB</th>
                  <th>Carbs</th>
                  <th>Trend</th>
                  <th>Type</th>
                  <th>Outcome</th>
                  <th>Review</th>
                  <th>Delete</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => {
                  const in_ = r.input_summary || {}
                  return (
                    <Fragment key={r.id}>
                      <tr className={expandedId === r.id ? 'row-expanded' : ''}>
                        <td>{r.created_at ? new Date(r.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—'}</td>
                        <td>{in_.glucose_level ?? '—'}</td>
                        <td>{in_.iob ?? '—'}</td>
                        <td>{in_.anticipated_carbs ?? '—'}</td>
                        <td>{in_.glucose_trend ? String(in_.glucose_trend).replace(/_/g, ' ') : '—'}</td>
                        <td>{formatType(r.endpoint)}</td>
                        <td>{formatOutcome(r.predicted_class)}</td>
                        <td>
                          {r.is_high_risk ? (
                            <button
                              type="button"
                              className="btn btn-sm reports-review-btn"
                              onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
                              aria-expanded={expandedId === r.id}
                              title="Open details for clinical review"
                            >
                              Review
                            </button>
                          ) : (
                            <span className="badge badge-ok">OK</span>
                          )}
                        </td>
                        <td className="reports-actions-cell">
                          <button
                            type="button"
                            className="btn btn-sm reports-delete-btn"
                            disabled={deletingId === r.id}
                            onClick={() => handleDeleteRecord(r.id)}
                            title="Delete this report"
                          >
                            {deletingId === r.id ? 'Deleting…' : 'Delete'}
                          </button>
                        </td>
                      </tr>
                      {expandedId === r.id && (getInputSummaryDisplay(r.input_summary).length > 0 || (r.response_summary && Object.keys(r.response_summary).length > 0)) && (
                        <tr key={`${r.id}-detail`} className="row-detail">
                          <td colSpan={9}>
                            <div className="reports-detail-panel">
                              {getInputSummaryDisplay(r.input_summary).length > 0 && (
                                <div className="reports-detail-block">
                                  <h4>Assessment context</h4>
                                  <dl className="reports-detail-list">
                                    {getInputSummaryDisplay(r.input_summary).map(({ label, value }) => (
                                      <div key={label} className="reports-detail-row">
                                        <dt>{label}</dt>
                                        <dd>{value}</dd>
                                      </div>
                                    ))}
                                  </dl>
                                </div>
                              )}
                              {r.response_summary && Object.keys(r.response_summary).length > 0 && (
                                <div className="reports-detail-block">
                                  <h4>Recommendation</h4>
                                  <dl className="reports-detail-list">
                                    {r.response_summary.dosage_action && (
                                      <div className="reports-detail-row">
                                        <dt>Action</dt>
                                        <dd>{r.response_summary.dosage_action}</dd>
                                      </div>
                                    )}
                                    <div className="reports-detail-row">
                                      <dt>Outcome</dt>
                                      <dd>{formatOutcome(r.response_summary.predicted_class)}</dd>
                                    </div>
                                    {r.response_summary.confidence != null && (
                                      <div className="reports-detail-row">
                                        <dt>Confidence</dt>
                                        <dd>{(r.response_summary.confidence * 100).toFixed(0)}%</dd>
                                      </div>
                                    )}
                                  </dl>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
