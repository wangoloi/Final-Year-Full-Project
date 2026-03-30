/**
 * Patients page: list, register, edit patients.
 * Links to patient records.
 */
import { useState, useEffect } from 'react'
import { useClinical } from '../context/ClinicalContext'
import { FiUserPlus, FiEdit2, FiFileText, FiUsers, FiTrash2, FiRotateCcw } from 'react-icons/fi'
import PatientForm from '../components/patients/PatientForm'
import PatientRecords from '../components/patients/PatientRecords'
import BackupSection from '../components/patients/BackupSection'
import {
  fetchPatient,
  fetchDeletedPatients,
  deletePatient,
  restorePatient,
  purgePatient,
} from '../services/patientsApi'

export default function Patients() {
  const { patients, refreshPatients, setSelectedPatientId, setPatient, selectedPatientId } = useClinical()
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState(null)
  const [viewingPatient, setViewingPatient] = useState(null)
  const [viewingPatientData, setViewingPatientData] = useState(null)
  const [deletedPatients, setDeletedPatients] = useState([])

  const loadDeleted = async () => {
    const { patients: list } = await fetchDeletedPatients()
    setDeletedPatients(list || [])
  }

  useEffect(() => {
    refreshPatients()
  }, [refreshPatients])

  useEffect(() => {
    loadDeleted()
  }, [patients])

  useEffect(() => {
    if (!viewingPatient) {
      setViewingPatientData(null)
      return
    }
    fetchPatient(viewingPatient).then((p) => setViewingPatientData(p))
  }, [viewingPatient])

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
    setPatient?.({ name: p.name, condition: p.condition })
  }

  const handleDelete = async (p) => {
    const ok = window.confirm(
      `Delete "${p.name}"? They will be removed from the active list and assessments until you restore them from Deleted patients below. Linked assessment history is kept until you permanently delete.`
    )
    if (!ok) return
    const result = await deletePatient(p.id)
    if (!result.ok) {
      window.alert(result.error || 'Could not delete patient')
      return
    }
    if (selectedPatientId === p.id) {
      setSelectedPatientId?.(null)
      setPatient?.({ name: '', condition: '' })
    }
    if (viewingPatient === p.id) {
      setViewingPatient(null)
      setViewingPatientData(null)
    }
    await refreshPatients()
    await loadDeleted()
  }

  const handleRestore = async (p) => {
    const result = await restorePatient(p.id)
    if (!result.ok) {
      window.alert(result.error || 'Could not restore patient')
      return
    }
    await refreshPatients()
    await loadDeleted()
  }

  const handlePurge = async (p) => {
    const ok = window.confirm(
      `Permanently delete "${p.name}"? This removes the patient and all linked assessment records. This cannot be undone.`
    )
    if (!ok) return
    const result = await purgePatient(p.id)
    if (!result.ok) {
      window.alert(result.error || 'Could not delete patient')
      return
    }
    if (selectedPatientId === p.id) {
      setSelectedPatientId?.(null)
      setPatient?.({ name: '', condition: '' })
    }
    await refreshPatients()
    await loadDeleted()
  }

  const handleBackToList = () => {
    setViewingPatient(null)
  }

  if (viewingPatient && viewingPatientData) {
    return (
      <div className="page">
        <div style={{ marginBottom: 'var(--spacing-lg)', display: 'flex', alignItems: 'center' }}>
          <button type="button" className="btn btn-secondary" onClick={() => setViewingPatient(null)}>
            ← Back to list
          </button>
        </div>
        <PatientRecords patient={viewingPatientData} />
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Patients</h1>
          <p className="page-description">
            Register and manage patients. Delete removes a patient from the active list (you can restore them and their linked data below).
            Permanent delete removes the patient and all linked records.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={handleAdd}>
          <FiUserPlus size={18} /> Register patient
        </button>
      </div>

      {showForm ? (
        <PatientForm
          initialData={editingPatient}
          onSuccess={handleFormSuccess}
          onCancel={() => { setShowForm(false); setEditingPatient(null) }}
        />
      ) : (
        <div className="card">
          <h2 className="card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FiUsers size={20} /> Registered patients ({patients.length})
          </h2>
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
                      className="btn btn-outline-danger"
                      onClick={() => handleDelete(p)}
                      title="Delete patient (can restore later)"
                    >
                      <FiTrash2 size={16} /> Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!showForm && (
        <div className="card" style={{ marginTop: 'var(--spacing-lg)' }}>
          <h2 className="card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FiTrash2 size={20} /> Deleted patients ({deletedPatients.length})
          </h2>
          <p className="card-description">
            Deleted patients are hidden from the active list and cannot receive new assessments until restored. Permanently delete to remove all linked records.
          </p>
          {deletedPatients.length === 0 ? (
            <p className="card-description" style={{ marginTop: 0 }}>
              No deleted patients.
            </p>
          ) : (
            <div className="patient-list">
              {deletedPatients.map((p) => (
                <div key={p.id} className="patient-list-item">
                  <div>
                    <div className="patient-name">{p.name}</div>
                    <div className="patient-meta">
                      {p.condition}
                      {p.deleted_at && (
                        <span>
                          {' '}
                          • Deleted {new Date(p.deleted_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="patient-list-actions">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => handleRestore(p)}
                      title="Restore patient and linked data to active list"
                    >
                      <FiRotateCcw size={16} /> Restore
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-danger"
                      onClick={() => handlePurge(p)}
                      title="Permanently delete all data"
                    >
                      <FiTrash2 size={16} /> Delete permanently
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <BackupSection />
    </div>
  )
}
