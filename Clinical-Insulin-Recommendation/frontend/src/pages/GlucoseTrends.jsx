import { useState, useEffect } from 'react'
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer, Area } from 'recharts'
import { useClinical } from '../context/ClinicalContext'
import { apiFetch } from '../api'

const API = '/api'

export default function GlucoseTrends() {
  const { recentMetrics } = useClinical()
  const [range, setRange] = useState('24h')
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(true)

  const hoursMap = { '6h': 6, '12h': 12, '24h': 24, '72h': 72 }

  useEffect(() => {
    const hours = hoursMap[range] || 24
    setLoading(true)
    apiFetch(`${API}/glucose-trends?hours=${hours}&_=${Date.now()}`)
      .then((r) => (r.ok ? r.json() : Promise.resolve({ series: [] })))
      .then((d) => setChartData(Array.isArray(d.series) && d.series.length ? d.series : []))
      .catch(() => setChartData([]))
      .finally(() => setLoading(false))
  }, [range])

  return (
    <div className="page-trends">
      <div className="page-header">
        <h1 className="page-title">Glucose trends</h1>
        <p className="page-description">Historical and predicted glucose from your assessments. Target range 70–180 mg/dL. Data appears after you submit an assessment on the Dashboard.</p>
      </div>
      <div className="card card-chart">
        <div className="card-chart-header">
          <h2 className="card-heading">Glucose over time</h2>
          <div className="chart-range">
            {['6h', '12h', '24h', '72h'].map((r) => (
              <button key={r} type="button" className={`chart-range-btn ${range === r ? 'active' : ''}`} onClick={() => setRange(r)}>{r}</button>
            ))}
          </div>
        </div>
        {loading ? (
          <div className="chart-empty-state"><p className="chart-empty-description">Loading…</p></div>
        ) : chartData.length === 0 ? (
          <div className="chart-empty-state" aria-live="polite">
            <p className="chart-empty-title">No trend data yet</p>
            <p className="chart-empty-description">Complete an assessment on the Dashboard and get a recommendation. Your glucose readings will be recorded and shown here.</p>
          </div>
        ) : (
          <>
            <div className="chart-container chart-container-lg">
              <ResponsiveContainer width="100%" height={360}>
                <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                  <defs>
                    <linearGradient id="trendTargetBand" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stopColor="var(--chart-target)" stopOpacity="0.12" />
                      <stop offset="1" stopColor="var(--chart-target)" stopOpacity="0.04" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
                  <YAxis domain={[60, 220]} tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
                  <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid var(--border)' }} formatter={(v) => [`${v} mg/dL`, '']} />
                  <ReferenceLine y={70} stroke="var(--chart-low)" strokeDasharray="4 4" />
                  <ReferenceLine y={180} stroke="var(--chart-high)" strokeDasharray="4 4" />
                  <Area type="monotone" dataKey="actual" fill="url(#trendTargetBand)" stroke="none" />
                  <Line type="monotone" dataKey="actual" stroke="var(--chart-actual)" strokeWidth={2} name="Actual" dot={false} />
                  <Line type="monotone" dataKey="predicted" stroke="var(--chart-predicted)" strokeWidth={2} strokeDasharray="5 5" name="Predicted" dot={false} />
                  <Legend />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-legend-note">Data from assessment entries. Event markers reflect meals and insulin from the care plan.</p>
          </>
        )}
      </div>
      {recentMetrics.glucose != null && (
        <div className="card card-metric-summary">
          <h2 className="card-heading">Latest reading</h2>
          <p className="metric-summary-value">{recentMetrics.glucose} <span className="metric-unit">{recentMetrics.glucoseUnit || 'mg/dL'}</span></p>
          {recentMetrics.timestamp && <p className="text-muted">{new Date(recentMetrics.timestamp).toLocaleString()}</p>}
        </div>
      )}
    </div>
  )
}
