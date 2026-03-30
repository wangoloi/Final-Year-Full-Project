import { useState, useEffect, useMemo, useRef, useCallback, useId } from 'react'
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Area,
} from 'recharts'
import { useClinical } from '../context/ClinicalContext'
import { apiFetch } from '../api'

const API = '/api'

const TARGET_LOW = 70
const TARGET_HIGH = 180

/** Common IANA zones → short abbreviations (EAT, ET, …). Unknown zones use Intl or the IANA id. */
const IANA_TO_ABBREV = {
  UTC: 'UTC',
  'Africa/Kampala': 'EAT',
  'Africa/Nairobi': 'EAT',
  'Africa/Addis_Ababa': 'EAT',
  'Africa/Dar_es_Salaam': 'EAT',
  'Africa/Johannesburg': 'SAST',
  'Africa/Cairo': 'EET',
  'Africa/Lagos': 'WAT',
  'America/New_York': 'ET',
  'America/Chicago': 'CT',
  'America/Denver': 'MT',
  'America/Los_Angeles': 'PT',
  'America/Phoenix': 'MST',
  'America/Toronto': 'ET',
  'Europe/London': 'GMT',
  'Europe/Paris': 'CET',
  'Europe/Berlin': 'CET',
  'Asia/Dubai': 'GST',
  'Asia/Tokyo': 'JST',
  'Asia/Singapore': 'SGT',
  'Asia/Kolkata': 'IST',
  'Australia/Sydney': 'AEST',
}

function getTimeZoneAbbreviation(iana) {
  if (!iana) return ''
  if (IANA_TO_ABBREV[iana]) return IANA_TO_ABBREV[iana]
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: iana,
      timeZoneName: 'short',
    }).formatToParts(new Date())
    const name = parts.find((p) => p.type === 'timeZoneName')?.value
    return name || iana
  } catch {
    return iana
  }
}

function formatTimeZoneOptionLabel(iana) {
  const ab = getTimeZoneAbbreviation(iana)
  const tail = iana.includes('/') ? iana.split('/').slice(-1)[0].replace(/_/g, ' ') : iana
  return `${ab} — ${tail}`
}

/** Parse server ISO / SQLite-style timestamps to UTC milliseconds (never epoch placeholders). */
function parseIsoToMs(iso) {
  if (iso == null || iso === '') return NaN
  if (typeof iso === 'number' && Number.isFinite(iso)) return iso
  const s = String(iso).trim()
  if (!s) return NaN
  // Normalize "YYYY-MM-DD HH:MM..." (SQLite / Python str(datetime)) → T separator for ECMAScript parsers
  let normalized = s.replace(/^(\d{4}-\d{2}-\d{2})\s+(\d)/, '$1T$2')
  let t = new Date(normalized).getTime()
  if (Number.isFinite(t)) return t
  const parsed = Date.parse(normalized)
  if (Number.isFinite(parsed)) return parsed
  // Naive local clock time without offset → treat as UTC for chart consistency with backend Z output
  const m = normalized.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)/)
  if (m) {
    t = new Date(`${m[1]}T${m[2]}Z`).getTime()
    if (Number.isFinite(t)) return t
  }
  return NaN
}

function getTimeZoneOptions() {
  try {
    if (typeof Intl.supportedValuesOf === 'function') {
      return [...Intl.supportedValuesOf('timeZone')].sort()
    }
  } catch {
    /* ignore */
  }
  return [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Africa/Johannesburg',
    'Asia/Tokyo',
    'Australia/Sydney',
  ]
}

function formatGlucoseDateTime(iso, timeZone) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return String(iso)
    const opts = {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...(timeZone ? { timeZone } : {}),
    }
    return d.toLocaleString(undefined, opts)
  } catch {
    return String(iso)
  }
}

function GlucoseTooltip({ active, payload, label, timeZone }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  const iso = row?.iso
  let when = label
  if (iso) {
    try {
      when = formatGlucoseDateTime(iso, timeZone)
    } catch {
      when = label
    }
  }
  return (
    <div
      style={{
        borderRadius: 8,
        border: '1px solid var(--border)',
        background: 'var(--bg-card)',
        padding: '0.65rem 0.85rem',
        fontSize: '0.85rem',
        boxShadow: 'var(--shadow)',
      }}
    >
      <div style={{ color: 'var(--text-muted)', marginBottom: '0.35rem' }}>{when}</div>
      {row?.patientName && (
        <div style={{ color: 'var(--text-muted)', marginBottom: '0.35rem', fontSize: '0.8rem' }}>{row.patientName}</div>
      )}
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: 'var(--text)' }}>
          <strong>{p.name}:</strong> {typeof p.value === 'number' ? Math.round(p.value) : p.value} mg/dL
        </div>
      ))}
    </div>
  )
}

const LIVE_REFRESH_MS = 60_000

export default function GlucoseTrends() {
  const { recentMetrics, patients } = useClinical()
  const defaultTz = useMemo(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    } catch {
      return 'UTC'
    }
  }, [])
  const [timeZone, setTimeZone] = useState(defaultTz)
  const [recordLimit, setRecordLimit] = useState(50)
  const [trendPatientId, setTrendPatientId] = useState(null)
  const [patientMenuOpen, setPatientMenuOpen] = useState(false)
  const patientMenuRef = useRef(null)
  const [chartData, setChartData] = useState([])
  const [trendMeta, setTrendMeta] = useState({
    limit: 50,
    patientId: null,
    windowMode: 'recent',
    timezone: null,
  })
  const [loading, setLoading] = useState(true)
  const gradientId = `trend-fill-${useId().replace(/:/g, '')}`

  const tzOptions = useMemo(() => {
    const list = [...getTimeZoneOptions()]
    if (timeZone && !list.includes(timeZone)) list.unshift(timeZone)
    return list.sort()
  }, [timeZone])
  const fetchKeyRef = useRef(0)

  const loadTrends = useCallback((opts = { silent: false }) => {
    const silent = opts.silent === true
    let url = `${API}/glucose-trends?limit=${recordLimit}&timezone=${encodeURIComponent(timeZone)}&_=${Date.now()}`
    if (trendPatientId != null) url += `&patient_id=${trendPatientId}`
    const req = ++fetchKeyRef.current
    if (!silent) setLoading(true)
    apiFetch(url)
      .then((r) => (r.ok ? r.json() : Promise.resolve({ series: [] })))
      .then((d) => {
        if (req !== fetchKeyRef.current) return
        const series = Array.isArray(d.series) && d.series.length ? d.series : []
        setChartData(series)
        setTrendMeta({
          limit: typeof d.limit === 'number' ? d.limit : recordLimit,
          patientId: d.patient_id != null ? d.patient_id : null,
          windowMode: d.window_mode ?? 'recent',
          timezone: d.timezone ?? timeZone,
        })
      })
      .catch(() => {
        if (req !== fetchKeyRef.current) return
        setChartData([])
      })
      .finally(() => {
        if (req === fetchKeyRef.current && !silent) setLoading(false)
      })
  }, [recordLimit, timeZone, trendPatientId])

  useEffect(() => {
    loadTrends({ silent: false })
  }, [loadTrends])

  useEffect(() => {
    const id = setInterval(() => loadTrends({ silent: true }), LIVE_REFRESH_MS)
    return () => clearInterval(id)
  }, [loadTrends])

  useEffect(() => {
    const onDoc = (e) => {
      if (!patientMenuRef.current?.contains(e.target)) setPatientMenuOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const trendPatientLabel = useMemo(() => {
    if (trendPatientId == null) return 'All patients'
    const p = (patients || []).find((x) => x.id === trendPatientId || String(x.id) === String(trendPatientId))
    return p?.name || `Patient #${trendPatientId}`
  }, [patients, trendPatientId])

  const singlePatient = trendPatientId != null

  const chartRows = useMemo(() => {
    return (chartData || []).flatMap((row) => {
      const xMs = parseIsoToMs(row.iso)
      if (!Number.isFinite(xMs)) return []
      const pid = row.patient_id
      const p =
        pid != null ? (patients || []).find((x) => x.id === pid || String(x.id) === String(pid)) : null
      const patientName = p?.name ?? (pid != null ? `Patient #${pid}` : null)
      return [{ ...row, xMs, patientName }]
    })
  }, [chartData, patients])

  const xDomain = useMemo(() => ['dataMin', 'dataMax'], [])

  const formatXAxisTick = useCallback(
    (value) => {
      if (value == null || !Number.isFinite(Number(value))) return ''
      try {
        const d = new Date(Number(value))
        if (Number.isNaN(d.getTime())) return ''
        const opts = {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZone,
        }
        return d.toLocaleString(undefined, opts)
      } catch {
        return ''
      }
    },
    [timeZone],
  )

  const showPredicted = useMemo(
    () =>
      chartRows.some((row) => {
        const a = Number(row.actual)
        const p = Number(row.predicted)
        return !Number.isNaN(a) && !Number.isNaN(p) && Math.abs(a - p) > 0.75
      }),
    [chartRows],
  )

  const yDomain = useMemo(() => {
    if (!chartRows.length) return [40, 220]
    let maxV = TARGET_HIGH
    let minV = TARGET_LOW
    for (const row of chartRows) {
      const a = Number(row.actual)
      const p = Number(row.predicted)
      if (!Number.isNaN(a)) {
        maxV = Math.max(maxV, a)
        minV = Math.min(minV, a)
      }
      if (!Number.isNaN(p)) {
        maxV = Math.max(maxV, p)
        minV = Math.min(minV, p)
      }
    }
    const span = Math.max(maxV - minV, 40)
    const pad = Math.max(12, span * 0.1)
    const lo = Math.max(0, Math.floor(minV - pad))
    const hi = Math.ceil(maxV + pad)
    return [lo, Math.max(hi, TARGET_HIGH + 20)]
  }, [chartRows])

  const selectPatient = useCallback((id) => {
    setTrendPatientId(id)
    setPatientMenuOpen(false)
  }, [])

  const tzAbbrev = useMemo(() => getTimeZoneAbbreviation(timeZone), [timeZone])

  const chartMargins = { top: 12, right: 12, left: 4, bottom: singlePatient ? 48 : 52 }
  const liveLabel = 'Live: refreshes every minute'

  return (
    <div className="page-trends">
      <div className="page-header">
        <h1 className="page-title">Glucose trends</h1>
        <p className="page-description">
          Shows the <strong>most recent</strong> assessment glucose readings (count you choose). Times on the axis use the selected <strong>time zone</strong> for display. The chart refreshes every minute.
        </p>
      </div>
      <div className="card card-chart">
        <div className="card-chart-header card-chart-header--stacked">
          <div className="card-chart-header-row">
            <div className="card-chart-title-row">
              <h2 className="card-heading">Glucose over time</h2>
              <div className="chart-patient-filter" ref={patientMenuRef}>
              <button
                type="button"
                className="btn btn-secondary btn-sm chart-patient-trend-btn"
                aria-expanded={patientMenuOpen}
                aria-haspopup="listbox"
                onClick={() => setPatientMenuOpen((o) => !o)}
              >
                <span className="chart-patient-trend-label">Patient trend</span>
                <span className="chart-patient-trend-current" title={trendPatientLabel}>
                  {trendPatientLabel}
                </span>
                <span className="chart-patient-trend-chevron" aria-hidden>▾</span>
              </button>
              {patientMenuOpen && (
                <ul className="chart-patient-menu" role="listbox">
                  <li role="option">
                    <button type="button" className={trendPatientId == null ? 'is-active' : ''} onClick={() => selectPatient(null)}>
                      All patients
                    </button>
                  </li>
                  {(patients || []).length === 0 ? (
                    <li className="chart-patient-menu-empty" aria-disabled>
                      <span>No patients registered</span>
                    </li>
                  ) : (
                    (patients || []).map((p) => (
                      <li key={p.id} role="option">
                        <button
                          type="button"
                          className={trendPatientId === p.id || String(trendPatientId) === String(p.id) ? 'is-active' : ''}
                          onClick={() => selectPatient(p.id)}
                        >
                          {p.name}
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              )}
              </div>
            </div>
          </div>
          <div className="chart-trends-toolbar">
            <label className="chart-trends-field chart-trends-field--tz">
              <span className="chart-trends-label">Time zone</span>
              <select
                className="form-input form-select chart-trends-tz"
                title={timeZone}
                value={timeZone}
                onChange={(e) => setTimeZone(e.target.value)}
              >
                {tzOptions.map((z) => (
                  <option key={z} value={z}>
                    {formatTimeZoneOptionLabel(z)}
                  </option>
                ))}
              </select>
            </label>
            <div className="chart-range" role="group" aria-label="Number of recent readings">
              {[10, 25, 50, 100].map((n) => (
                <button
                  key={n}
                  type="button"
                  className={`chart-range-btn ${recordLimit === n ? 'active' : ''}`}
                  onClick={() => setRecordLimit(n)}
                >
                  Last {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        {!loading && chartRows.length > 0 && (
          <p className="chart-patient-scope" role="status">
            {singlePatient ? (
              <>
                <strong>{trendPatientLabel}</strong> — last <strong>{trendMeta.limit ?? recordLimit}</strong> assessment glucose readings ({tzAbbrev}). {liveLabel}
              </>
            ) : (
              <>
                <strong>All patients</strong> — last <strong>{trendMeta.limit ?? recordLimit}</strong> readings across patients ({tzAbbrev}). {liveLabel}
              </>
            )}
          </p>
        )}

        {loading ? (
          <div className="chart-empty-state">
            <p className="chart-empty-description">Loading…</p>
          </div>
        ) : chartRows.length === 0 ? (
          <div className="chart-empty-state" aria-live="polite">
            <p className="chart-empty-title">No trend data yet</p>
            <p className="chart-empty-description">
              {chartData.length > 0
                ? 'Readings were returned but timestamps could not be parsed. Try refreshing or contact support if this persists.'
                : singlePatient
                  ? `No assessment glucose for ${trendPatientLabel} in the last ${recordLimit} readings. Complete an assessment with a glucose value, or try “All patients”.`
                  : `No assessment glucose in the last ${recordLimit} readings across patients.`}
            </p>
          </div>
        ) : (
          <>
            <div className={`chart-container chart-container-lg ${singlePatient ? 'chart-container--patient' : ''}`}>
              <ResponsiveContainer width="100%" height={singlePatient ? 400 : 380}>
                <ComposedChart data={chartRows} margin={chartMargins}>
                  <defs>
                    <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stopColor="var(--chart-actual)" stopOpacity="0.25" />
                      <stop offset="1" stopColor="var(--chart-actual)" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <ReferenceArea
                    y1={TARGET_LOW}
                    y2={TARGET_HIGH}
                    fill="var(--chart-target)"
                    fillOpacity={0.14}
                    strokeOpacity={0}
                  />
                  <XAxis
                    type="number"
                    dataKey="xMs"
                    domain={xDomain}
                    tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                    stroke="var(--border)"
                    tickLine={{ stroke: 'var(--border)' }}
                    angle={chartRows.length > 10 ? -22 : 0}
                    textAnchor={chartRows.length > 10 ? 'end' : 'middle'}
                    height={chartRows.length > 10 ? 56 : 40}
                    tickFormatter={formatXAxisTick}
                    interval="preserveStartAndEnd"
                    minTickGap={singlePatient ? 28 : 20}
                    label={{
                      value: `Time (${tzAbbrev})`,
                      position: 'insideBottom',
                      offset: -4,
                      style: { fontSize: 11, fill: 'var(--text-muted)', fontWeight: 600 },
                    }}
                  />
                  <YAxis
                    domain={yDomain}
                    tickCount={singlePatient ? 7 : 6}
                    tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                    stroke="var(--border)"
                    tickLine={{ stroke: 'var(--border)' }}
                    tickFormatter={(v) => (Number.isFinite(v) ? String(Math.round(v)) : '')}
                    width={52}
                    label={{
                      value: 'Glucose (mg/dL)',
                      angle: -90,
                      position: 'insideLeft',
                      offset: 2,
                      style: { fontSize: 11, fill: 'var(--text-muted)', fontWeight: 600 },
                    }}
                  />
                  <Tooltip content={(props) => <GlucoseTooltip {...props} timeZone={timeZone} />} />
                  <ReferenceLine y={TARGET_LOW} stroke="var(--chart-low)" strokeDasharray="4 4" strokeWidth={1.5} />
                  <ReferenceLine y={TARGET_HIGH} stroke="var(--chart-high)" strokeDasharray="4 4" strokeWidth={1.5} />
                  <Area type="monotone" dataKey="actual" fill={`url(#${gradientId})`} stroke="none" />
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="var(--chart-actual)"
                    strokeWidth={singlePatient ? 2.5 : 2}
                    name="Glucose"
                    dot={singlePatient ? { r: 3, strokeWidth: 1 } : false}
                    activeDot={{ r: 5 }}
                  />
                  {showPredicted && (
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      stroke="var(--chart-predicted)"
                      strokeWidth={2}
                      strokeDasharray="6 4"
                      name="Predicted"
                      dot={false}
                    />
                  )}
                  <Legend
                    wrapperStyle={{ fontSize: '0.85rem', paddingTop: 8 }}
                    formatter={(value) => (value === 'Glucose' ? 'Glucose (measured)' : value)}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-legend-note">
              {singlePatient
                ? `Shaded band: target range 70–180 mg/dL. Horizontal axis is local time (${tzAbbrev}).`
                : `Shaded band: target range 70–180 mg/dL. Hover shows patient; times are local (${tzAbbrev}).`}
            </p>
          </>
        )}
      </div>
      {recentMetrics.glucose != null && (
        <div className="card card-metric-summary">
          <h2 className="card-heading">Latest reading</h2>
          <p className="metric-summary-value">
            {recentMetrics.glucose} <span className="metric-unit">{recentMetrics.glucoseUnit || 'mg/dL'}</span>
          </p>
          {recentMetrics.timestamp && <p className="text-muted">{new Date(recentMetrics.timestamp).toLocaleString()}</p>}
        </div>
      )}
    </div>
  )
}
