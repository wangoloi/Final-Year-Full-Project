/**
 * Patient registration form.
 * Collects patient demographics for system registration.
 */
import { useState } from 'react'
import { useClinical } from '../../context/ClinicalContext'
import { createPatient, updatePatient } from '../../services/patientsApi'

const GENDER_OPTIONS = ['Male', 'Female', 'Other']
const CONDITION_T1D = 'Type 1 Diabetes'

export default function PatientForm({ onSuccess, onCancel, initialData }) {
  const { refreshPatients } = useClinical()
  const [form, setForm] = useState({
    name: initialData?.name ?? '',
    date_of_birth: initialData?.date_of_birth ?? '',
    gender: initialData?.gender ?? 'Male',
    condition: initialData?.condition ?? CONDITION_T1D,
    medical_record_number: initialData?.medical_record_number ?? '',
  })
  const [errors, setErrors] = useState([])
  const [saving, setSaving] = useState(false)

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => prev.filter((e) => e.field !== key))
  }

  const validate = () => {
    const errs = []
    const name = String(form.name || '').trim()
    if (!name) errs.push({ field: 'name', message: 'Name is required.' })
    if (name.length > 200) errs.push({ field: 'name', message: 'Name is too long.' })
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (errs.length > 0) {
      setErrors(errs)
      return
    }
    setSaving(true)
    setErrors([])
    try {
      const payload = {
        name: form.name.trim(),
        condition: form.condition.trim() || CONDITION_T1D,
        date_of_birth: form.date_of_birth?.trim() || null,
        gender: form.gender?.trim() || null,
        medical_record_number: form.medical_record_number?.trim() || null,
      }
      if (initialData?.id) {
        const result = await updatePatient(initialData.id, payload)
        if (!result.ok) {
          setErrors([{ field: '_', message: result.error }])
          return
        }
      } else {
        const result = await createPatient(payload)
        if (!result.ok) {
          setErrors([{ field: '_', message: result.error }])
          return
        }
      }
      await refreshPatients?.()
      onSuccess?.()
    } catch (err) {
      setErrors([{ field: '_', message: err.message || 'Failed to save patient.' }])
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2 className="card-heading">{initialData?.id ? 'Edit patient' : 'Register patient'}</h2>
      <p className="card-description">
        {initialData?.id
          ? 'Update patient information.'
          : 'Register a patient before running assessments. All assessments must be linked to a registered patient.'}
      </p>

      {errors.length > 0 && (
        <ul className="form-validation-errors" role="alert">
          {errors.map((err, i) => (
            <li key={i} data-field={err.field}>
              {err.message}
            </li>
          ))}
        </ul>
      )}

      <div className="form-grid">
        <label className="form-field">
          <span className="form-field-label">Full name *</span>
          <input
            type="text"
            className="form-input"
            value={form.name}
            onChange={(e) => handleChange('name', e.target.value)}
            placeholder="e.g. John Doe"
            required
            disabled={saving}
          />
        </label>

        <label className="form-field">
          <span className="form-field-label">Date of birth</span>
          <input
            type="date"
            className="form-input"
            value={form.date_of_birth}
            onChange={(e) => handleChange('date_of_birth', e.target.value)}
            disabled={saving}
          />
        </label>

        <label className="form-field">
          <span className="form-field-label">Gender</span>
          <select
            className="form-select"
            value={form.gender}
            onChange={(e) => handleChange('gender', e.target.value)}
            disabled={saving}
          >
            {GENDER_OPTIONS.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span className="form-field-label">Condition</span>
          <input
            type="text"
            className="form-input"
            value={form.condition}
            onChange={(e) => handleChange('condition', e.target.value)}
            placeholder="e.g. Type 1 Diabetes"
            disabled={saving}
          />
        </label>

        <label className="form-field form-field-full">
          <span className="form-field-label">Medical record number</span>
          <input
            type="text"
            className="form-input"
            value={form.medical_record_number}
            onChange={(e) => handleChange('medical_record_number', e.target.value)}
            placeholder="Optional"
            disabled={saving}
          />
        </label>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving...' : initialData?.id ? 'Update' : 'Register'}
        </button>
        {onCancel && (
          <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
