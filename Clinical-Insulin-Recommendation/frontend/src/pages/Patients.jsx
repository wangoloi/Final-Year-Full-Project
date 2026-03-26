/**
 * Patients page: list, register, edit patients.
 * Links to patient records.
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClinical } from '../context/ClinicalContext'
import { FiUserPlus, FiEdit2, FiFileText, FiUsers } from 'react-icons/fi'
import PatientForm from '../components/patients/PatientForm'
import PatientRecords from '../components/patients/PatientRecords'
import BackupSection from '../components/patients/BackupSection'
import { fetchPatients, fetchPatient } from '../services/patientsApi'

export default function Patients() {
  const { patients, refreshPatients, setSelectedPatientId, setPatient } = useClinical()
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState(null)
  const [viewingPatient, setViewingPatient] = useState(null)
  const [viewingPatientData, setViewingPatientData] = useState(null)

  useEffect(() => {
    refreshPatients()
  }, [refreshPatients])

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
            Register and manage patients. Assessments can only be run for registered patients.
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
