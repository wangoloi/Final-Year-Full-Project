/**
 * Patients page: list, register, edit patients.
 * Links to patient records.
 */
import { useState, useEffect, useCallback } from 'react'
import { useClinical } from '../context/ClinicalContext'
import { FiUserPlus, FiEdit2, FiFileText, FiUsers, FiDatabase, FiRefreshCw, FiTrash2, FiRotateCcw, FiEye, FiEyeOff } from 'react-icons/fi'
import PatientForm from '../components/patients/PatientForm'
import PatientRecords from '../components/patients/PatientRecords'
import BackupSection from '../components/patients/BackupSection'
import {
  fetchPatients,
  fetchPatient,
  fetchRemovedPatients,
  seedDemoPatients,
  deletePatient,
  restorePatient,
} from '../services/patientsApi'

const ACTIONS_HIDDEN_STORAGE_KEY = 'glucosense_patients_actions_hidden'

export default function Patients() {
  const { patients, refreshPatients, setSelectedPatientId, setPatient, selectedPatientId } = useClinical()
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState(null)
  const [viewingPatient, setViewingPatient] = useState(null)
  const [viewingPatientData, setViewingPatientData] = useState(null)
  const [patientDetailLoading, setPatientDetailLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [demoMessage, setDemoMessage] = useState(null)
  const [removedPatients, setRemovedPatients] = useState([])
  const [removedLoadError, setRemovedLoadError] = useState(null)
  const [actionsHidden, setActionsHidden] = useState(() => {
    try {
      return localStorage.getItem(ACTIONS_HIDDEN_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })

  const loadRemoved = useCallback(async () => {
    setRemovedLoadError(null)
    const { patients: list, error } = await fetchRemovedPatients()
    setRemovedPatients(list)
    setRemovedLoadError(error || null)
  }, [])

  useEffect(() => {
    refreshPatients()
    loadRemoved()
  }, [refreshPatients, loadRemoved])

  useEffect(() => {
    if (!viewingPatient) {
      setViewingPatientData(null)
      setPatientDetailLoading(false)
      return
    }
    setPatientDetailLoading(true)
    fetchPatient(viewingPatient)
      .then((p) => setViewingPatientData(p))
      .finally(() => setPatientDetailLoading(false))
  }, [viewingPatient])

  useEffect(() => {
    try {
      localStorage.setItem(ACTIONS_HIDDEN_STORAGE_KEY, actionsHidden ? '1' : '0')
    } catch (_) {}
  }, [actionsHidden])

  const handleAdd = () => {
    setEditingPatient(null)
    setShowForm(true)
  }

  const handleEdit = (p) => {
    setEditingPatient(p)
    setShowForm(true)
  }

  const handleFormSuccess = () => {
    setShowForm(false)
    setEditingPatient(null)
    refreshPatients()
  }

  const handleViewRecords = (p) => {
    setViewingPatient(p.id)
    setSelectedPatientId?.(p.id)
    setPatient?.(p.name, p.condition)
  }

  const handleBackToList = () => {
    setViewingPatient(null)
  }

  const handleDelete = async (p) => {
    if (
      !window.confirm(
        `Remove ${p.name} from the active list? Their assessments, glucose, and dose history stay in the database. You can retrieve them below under "Removed patients".`,
      )
    ) {
      return
    }
    setDemoMessage(null)
    const result = await deletePatient(p.id)
    if (!result.ok) {
      setDemoMessage(result.error || 'Could not delete patient.')
      return
    }
    if (selectedPatientId === p.id) {
      setSelectedPatientId?.(null)
    }
    await refreshPatients()
    await loadRemoved()
    setDemoMessage(`${p.name} was removed. You can restore them under Removed patients.`)
  }

  const handleRestore = async (p) => {
    setDemoMessage(null)
    try {
      const result = await restorePatient(p.id)
      if (!result.ok) {
        setDemoMessage(result.error || 'Could not restore patient.')
        return
      }
      await refreshPatients()
      await loadRemoved()
      const extra = result.warning ? ` ${result.warning}` : ''
      setDemoMessage(`${p.name} was restored to the active list.${extra}`)
    } catch (e) {
      setDemoMessage(e?.message || 'Could not reach the server to restore this patient.')
    }
  }

  const handleLoadDemo = async (force = false) => {
    setDemoMessage(null)
    setDemoLoading(true)
    try {
      const result = await seedDemoPatients(force)
      if (!result.ok) {
        setDemoMessage(result.error || 'Could not load demo data.')
        return
      }
      await refreshPatients()
      const n = result.monitoring_seeded_for
      setDemoMessage(
        force
          ? `Demo patients updated. Refreshed monitoring data for ${n} patient(s).`
          : n > 0
            ? `Added demo patients and monitoring data for ${n} patient(s).`
            : 'Demo patients are already present with data. Use refresh to replace readings.',
      )
    } finally {
      setDemoLoading(false)
    }
  }

  if (viewingPatient) {
    const patientForRecords =
      viewingPatientData || patients.find((p) => Number(p.id) === Number(viewingPatient))
    return (
      <div className="page">
        <div style={{ marginBottom: 'var(--spacing-lg)', display: 'flex', alignItems: 'center' }}>
          <button type="button" className="btn btn-secondary" onClick={() => setViewingPatient(null)}>
            ← Back to list
          </button>
        </div>
        {patientDetailLoading && !patientForRecords ? (
          <div className="card">
            <p className="card-description">Loading patient…</p>
          </div>
        ) : patientForRecords ? (
          <PatientRecords patient={patientForRecords} />
        ) : (
          <div className="card">
            <p className="card-description">
              Could not load this patient from the server. Go back and try again, or check that the API is running.
            </p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Patients</h1>
          <p className="page-description">
            Register and manage patients. Assessments can only be run for registered patients.
          </p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={demoLoading}
            onClick={() => handleLoadDemo(false)}
            title="Creates named demo patients (if missing) and adds ~72h of glucose, assessments, and doses"
          >
            <FiDatabase size={18} /> {demoLoading ? 'Loading…' : 'Load demo patients'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={demoLoading}
            onClick={() => handleLoadDemo(true)}
            title="Clears and re-seeds monitoring data for the demo cohort only"
          >
            <FiRefreshCw size={18} /> Refresh demo data
          </button>
          <button type="button" className="btn btn-primary" onClick={handleAdd}>
            <FiUserPlus size={18} /> Register patient
          </button>
        </div>
      </div>
      {demoMessage && (
        <p className="card-description" style={{ marginTop: '-0.5rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
          {demoMessage}
        </p>
      )}

      {showForm ? (
        <PatientForm
          initialData={editingPatient}
          onSuccess={handleFormSuccess}
          onCancel={() => { setShowForm(false); setEditingPatient(null) }}
        />
      ) : (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h2 className="card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <FiUsers size={20} /> Registered patients ({patients.length})
            </h2>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setActionsHidden((v) => !v)}
              title={actionsHidden ? 'Unhide patient action buttons' : 'Hide patient action buttons'}
            >
              {actionsHidden ? <FiEye size={16} /> : <FiEyeOff size={16} />}{' '}
              {actionsHidden ? 'Unhide actions' : 'Hide actions'}
            </button>
          </div>
          {patients.length === 0 ? (
            <p className="card-description">
              No patients registered. Click &quot;Register patient&quot; to add one. You must register a patient before running assessments.
            </p>
          ) : (
            <div className="patient-list">
              {patients.map((p) => (
                <div key={p.id} className="patient-list-item">
                  <div>
                    <div className="patient-name">{p.name}</div>
                    <div className="patient-meta">
                      {p.condition}
                      {p.medical_record_number && ` • MRN: ${p.medical_record_number}`}
                    </div>
                  </div>
                  <div className="patient-list-actions">
                    {actionsHidden ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <button type="button" className="btn btn-secondary" onClick={() => setActionsHidden(false)} title="Unhide actions">
                          <FiEye size={16} /> Unhide
                        </button>
                      </div>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => handleViewRecords(p)}
                          title="View records"
                        >
                          <FiFileText size={16} /> Records
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => handleEdit(p)}
                          title="Edit"
                        >
                          <FiEdit2 size={16} /> Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => handleDelete(p)}
                          title="Remove patient"
                        >
                          <FiTrash2 size={16} /> Remove
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="card" style={{ marginTop: 'var(--spacing-lg)' }}>
        <h2 className="card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FiRotateCcw size={20} /> Removed patients ({removedPatients.length})
        </h2>
        <p className="card-description">
          Patients removed from the register can be brought back; their monitoring data is kept until you restore them.
        </p>
        {removedLoadError && (
          <p className="card-description" style={{ color: 'var(--danger, #b42318)', marginTop: '0.5rem' }}>
            {removedLoadError}
          </p>
        )}
        {!removedLoadError && removedPatients.length === 0 ? (
          <p className="card-description" style={{ margin: 0 }}>
            No removed patients.
          </p>
        ) : !removedLoadError ? (
          <div className="patient-list">
            {removedPatients.map((p) => (
              <div key={p.id} className="patient-list-item">
                <div>
                  <div className="patient-name">{p.name}</div>
                  <div className="patient-meta">
                    {p.condition}
                    {(p.medical_record_number || p.mrn_backup) &&
                      ` • MRN: ${p.medical_record_number || p.mrn_backup}`}
                    {p.deleted_at && (
                      <span>
                        {' '}
                        • Removed {new Date(p.deleted_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                      </span>
                    )}
                  </div>
                </div>
                <div className="patient-list-actions">
                  <button type="button" className="btn btn-primary" onClick={() => handleRestore(p)} title="Restore to active list">
                    <FiRotateCcw size={16} /> Retrieve / restore
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      <BackupSection />
    </div>
  )
}
