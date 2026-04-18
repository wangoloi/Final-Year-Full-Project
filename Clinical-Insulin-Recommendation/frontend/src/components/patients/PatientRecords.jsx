/**
 * Patient records view.
 * Displays glucose readings, assessments, and dose events for a patient.
 */
import { useState, useEffect } from 'react'
import {
  fetchPatientRecords,
  fetchPatientGlucoseReadings,
  fetchPatientDoseEvents,
  ensurePatientDemoMonitoring,
} from '../../services/patientsApi'
import { FiActivity, FiDroplet, FiFileText } from 'react-icons/fi'

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

function RecordsSection({ title, icon: Icon, items, emptyMessage, renderItem }) {
  return (
    <section className="card">
      <h3 className="records-section-header">
        {Icon && <Icon size={18} />}
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="card-description" style={{ margin: 0 }}>{emptyMessage}</p>
      ) : (
        <ul className="patient-records-list">
          {items.map((item, i) => (
            <li key={item.id ?? i} className="patient-record-item">
              {renderItem(item)}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default function PatientRecords({ patient }) {
  const [records, setRecords] = useState([])
  const [readings, setReadings] = useState([])
  const [doses, setDoses] = useState([])
  const [loading, setLoading] = useState(true)
  const [demoSeededNotice, setDemoSeededNotice] = useState(false)

  useEffect(() => {
    if (!patient?.id) return
    let cancelled = false
    setDemoSeededNotice(false)

    async function load() {
      setLoading(true)
      try {
        const ensured = await ensurePatientDemoMonitoring(patient.id)
        if (!cancelled && ensured.ok && ensured.seeded) {
          setDemoSeededNotice(true)
        }
        const [r, g, d] = await Promise.all([
          fetchPatientRecords(patient.id),
          fetchPatientGlucoseReadings(patient.id, 168),
          fetchPatientDoseEvents(patient.id),
        ])
        if (cancelled) return
        setRecords(Array.isArray(r?.records) ? r.records : [])
        setReadings(Array.isArray(g?.readings) ? g.readings : [])
        setDoses(Array.isArray(d?.events) ? d.events : [])
      } catch {
        if (!cancelled) {
          setRecords([])
          setReadings([])
          setDoses([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [patient?.id])

  if (!patient) return null
  if (loading) return <div className="card"><p>Loading records...</p></div>

  return (
    <div className="patient-records">
      <div className="card">
        <h2 className="card-heading">{patient.name}</h2>
        <p className="card-description">
          {patient.condition}
          {patient.medical_record_number && ` • MRN: ${patient.medical_record_number}`}
        </p>
        {demoSeededNotice && (
          <p className="card-description" style={{ marginTop: '0.5rem', color: 'var(--primary, #1976d2)' }}>
            Demo monitoring data was added so you can explore assessments, glucose, and doses. Replace with real
            assessments from the Dashboard when available.
          </p>
        )}
      </div>

      <RecordsSection
        title="Assessments"
        icon={FiFileText}
        items={records}
        emptyMessage="No assessments yet. Run an assessment from the Dashboard."
        renderItem={(r) => (
          <div>
            <div className="record-row-primary">{formatDate(r.created_at)}</div>
            <div className="record-row-secondary">
              {r.endpoint} • {r.predicted_class ?? '—'}
              {r.confidence != null
                ? ` (${r.confidence <= 1 ? Math.round(r.confidence * 100) : Math.round(r.confidence)}%)`
                : ''}
            </div>
          </div>
        )}
      />

      <RecordsSection
        title="Glucose readings"
        icon={FiDroplet}
        items={readings}
        emptyMessage="No glucose readings recorded for this patient."
        renderItem={(r) => (
          <div className="record-row">
            <span className="record-row-primary">{r.value} mg/dL</span>
            <span className="record-row-secondary">{formatDate(r.reading_at)}</span>
          </div>
        )}
      />

      <RecordsSection
        title="Dose events"
        icon={FiActivity}
        items={doses}
        emptyMessage="No dose events recorded."
        renderItem={(d) => (
          <div>
            <div className="record-row-primary">{formatDate(d.created_at)}</div>
            <div className="record-row-secondary">
              Meal: {d.meal_bolus ?? '—'} • Correction: {d.correction_dose ?? '—'} • Total: {d.total_dose ?? '—'}
            </div>
          </div>
        )}
      />
    </div>
  )
}
