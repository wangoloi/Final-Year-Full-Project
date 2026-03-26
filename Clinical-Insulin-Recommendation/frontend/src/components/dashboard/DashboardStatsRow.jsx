/**
 * Dashboard overview stats: assessments (recommend records), patients, report-ready days.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FiClipboard, FiUsers, FiFileText } from 'react-icons/fi'
import { useClinical } from '../../context/ClinicalContext'
import { fetchRecords } from '../../services/clinicalApi'
import { WORKSPACE_PATH } from '../../constants'

function getRecordDate(record) {
  if (!record?.created_at) return null
  const d = new Date(record.created_at)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function uniqueDatesWithRecords(records) {
  const set = new Set()
  records.forEach((r) => {
    const day = getRecordDate(r)
    if (day) set.add(day)
  })
  return set.size
}

export default function DashboardStatsRow() {
  const { patients } = useClinical()
  const [assessmentCount, setAssessmentCount] = useState(null)
  const [reportDays, setReportDays] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { records = [] } = await fetchRecords(500)
        if (cancelled) return
        const recommends = records.filter((r) => r.endpoint === 'recommend')
        setAssessmentCount(recommends.length)
        setReportDays(uniqueDatesWithRecords(records))
      } catch {
        if (!cancelled) {
          setAssessmentCount(0)
          setReportDays(0)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  const patientCount = patients?.length ?? 0

  return (
    <section className="dashboard-section" aria-labelledby="dashboard-stats-heading">
      <h2 id="dashboard-stats-heading" className="visually-hidden">Workspace statistics</h2>
      <div className="dash-stat-grid">
        <Link
          to={`${WORKSPACE_PATH}/assessment`}
          className="dash-stat-card dash-stat-card--assessment"
        >
          <div className="dash-stat-card-bg" aria-hidden />
          <div className="dash-stat-card-inner">
            <div className="dash-stat-icon-wrap">
              <FiClipboard size={22} strokeWidth={2} aria-hidden />
            </div>
            <div className="dash-stat-body">
              <span className="dash-stat-label">Assessments</span>
              <span className="dash-stat-value" aria-live="polite">
                {loading ? '—' : assessmentCount}
              </span>
              <span className="dash-stat-hint">Recommendation runs on record</span>
            </div>
          </div>
        </Link>

        <Link
          to={`${WORKSPACE_PATH}/patients`}
          className="dash-stat-card dash-stat-card--patients"
        >
          <div className="dash-stat-card-bg" aria-hidden />
          <div className="dash-stat-card-inner">
            <div className="dash-stat-icon-wrap">
              <FiUsers size={22} strokeWidth={2} aria-hidden />
            </div>
            <div className="dash-stat-body">
              <span className="dash-stat-label">Patients</span>
              <span className="dash-stat-value" aria-live="polite">
                {patientCount}
              </span>
              <span className="dash-stat-hint">Registered in workspace</span>
            </div>
          </div>
        </Link>

        <Link
          to={`${WORKSPACE_PATH}/reports`}
          className="dash-stat-card dash-stat-card--reports"
        >
          <div className="dash-stat-card-bg" aria-hidden />
          <div className="dash-stat-card-inner">
            <div className="dash-stat-icon-wrap">
              <FiFileText size={22} strokeWidth={2} aria-hidden />
            </div>
            <div className="dash-stat-body">
              <span className="dash-stat-label">Reports</span>
              <span className="dash-stat-value" aria-live="polite">
                {loading ? '—' : reportDays}
              </span>
              <span className="dash-stat-hint">Days with session data</span>
            </div>
          </div>
        </Link>
      </div>
    </section>
  )
}
