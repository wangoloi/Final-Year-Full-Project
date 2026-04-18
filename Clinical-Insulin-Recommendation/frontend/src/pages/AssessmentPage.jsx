/**
 * Assessment: patient selection, current assessment form, and recommendation results.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useClinical } from '../context/ClinicalContext'
import ConfirmDoseModal from '../components/ConfirmDoseModal'
import SuccessToast from '../components/SuccessToast'
import ResourcePanel from '../components/ResourcePanel'
import FeedbackModal from '../components/FeedbackModal'
import AssessmentForm from '../components/dashboard/AssessmentForm'
import RecommendationResult from '../components/dashboard/RecommendationResult'
import { fetchRecommendation, recordDose, submitFeedback, fetchPatientRecentActivity } from '../services/dashboardApi'
import { validateForm, buildBody, initialForm, DEFAULT_AGE } from '../utils/assessmentFormUtils'
import { DOSE_CONFIRM_DELAY_MS, WORKSPACE_PATH } from '../constants'

export default function AssessmentPage() {
  const { setRecentMetrics, recentMetrics, patients, selectedPatientId, setSelectedPatientId } = useClinical()
  const [form, setForm] = useState(initialForm)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState([])
  const [confirmDoseOpen, setConfirmDoseOpen] = useState(false)
  const [doseAdministering, setDoseAdministering] = useState(false)
  const [toastShow, setToastShow] = useState(false)
  const [resourcePanelOpen, setResourcePanelOpen] = useState(false)
  const [resourceId, setResourceId] = useState(null)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [feedbackModalVariant, setFeedbackModalVariant] = useState('override')
  const [feedbackSending, setFeedbackSending] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [toastMessage, setToastMessage] = useState('Dose recorded successfully.')
  const [quickEntryMode, setQuickEntryMode] = useState(false)
  const [patientRecentActivity, setPatientRecentActivity] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function loadRecent() {
      if (!selectedPatientId) {
        setPatientRecentActivity(null)
        return
      }
      const { ok, data } = await fetchPatientRecentActivity(selectedPatientId)
      if (!cancelled) {
        setPatientRecentActivity(ok ? data : null)
      }
    }
    loadRecent()
    return () => { cancelled = true }
  }, [selectedPatientId])

  useEffect(() => {
    if (!result) return
    setRecentMetrics({
      glucose: form.glucose_level ? Number(form.glucose_level) : null,
      carbohydrates: null,
      activityMinutes: form.physical_activity ? Number(form.physical_activity) : null,
    })
  }, [result, form.glucose_level, form.physical_activity, setRecentMetrics])

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setError(null)
    setFieldErrors((prev) => prev.filter((e) => e.field !== key))
  }

  const handleQuickEntryChange = (checked) => {
    setQuickEntryMode(checked)
  }

  const getRecommendation = async () => {
    if (!selectedPatientId) {
      setError('Select a patient first. Go to Patients to register one.')
      return
    }
    const formToValidate = quickEntryMode
      ? {
          ...initialForm(),
          age: DEFAULT_AGE,
          gender: 'Male',
          glucose_level: form.glucose_level,
          measurement_time: form.measurement_time || initialForm().measurement_time,
          meal_context: form.meal_context || 'fasting',
          activity_context: form.activity_context || 'resting',
          patient_id: selectedPatientId,
        }
      : { ...form, patient_id: selectedPatientId }
    const clientErrors = validateForm(formToValidate)
    if (clientErrors.length > 0) {
      setFieldErrors(clientErrors)
      setError('Please fix the errors below.')
      return
    }

    setFieldErrors([])
    setLoading(true)
    setError(null)
    setResult(null)

    const body = buildBody(
      quickEntryMode
        ? {
            ...initialForm(),
            age: DEFAULT_AGE,
            gender: 'Male',
            glucose_level: form.glucose_level,
            measurement_time: form.measurement_time || initialForm().measurement_time,
            meal_context: form.meal_context || 'fasting',
            activity_context: form.activity_context || 'resting',
            patient_id: selectedPatientId,
          }
        : { ...form, patient_id: selectedPatientId },
    )
    const { ok, data, status } = await fetchRecommendation(body)

    if (!ok) {
      if (status === 422 && Array.isArray(data.errors)) {
        setFieldErrors(data.errors)
        setError(data.detail || 'Validation failed.')
      } else {
        setError(data.detail || data.message || 'Request failed')
      }
      setLoading(false)
      return
    }

    setResult(data)
    try {
      const refreshed = await fetchPatientRecentActivity(selectedPatientId)
      if (refreshed.ok) setPatientRecentActivity(refreshed.data)
    } catch (_) {}
    setLoading(false)
  }

  const doseSummary = result
    ? {
        mealBolus: result.dosage_magnitude || 'Per protocol',
        correctionDose: result.dosage_action || '—',
        totalDose: result.recommendation_summary || 'See guidance',
      }
    : null

  const handleConfirmDose = async () => {
    setDoseAdministering(true)
    try {
      await recordDose({
        meal_bolus: doseSummary?.mealBolus,
        correction_dose: doseSummary?.correctionDose,
        total_dose: doseSummary?.totalDose,
        patient_id: selectedPatientId,
      })
    } catch (_) {}
    await new Promise((r) => setTimeout(r, DOSE_CONFIRM_DELAY_MS))
    setDoseAdministering(false)
    setConfirmDoseOpen(false)
    setToastMessage('Dose recorded successfully.')
    setToastShow(true)
  }

  const openResource = (id) => {
    setResourceId(id)
    setResourcePanelOpen(true)
  }

  const handleFeedbackSubmit = async (feedbackData) => {
    setFeedbackSending(true)
    try {
      const { ok, data } = await submitFeedback({
        request_id: result?.request_id,
        predicted_class: result?.predicted_class,
        clinician_action: feedbackData.clinician_action,
        actual_dose_units: feedbackData.actual_dose_units,
        override_reason: feedbackData.override_reason,
        input_summary: buildBody(form),
      })
      if (ok) {
        setFeedbackSent(true)
        setTimeout(() => {
          setFeedbackOpen(false)
          setFeedbackSent(false)
          setFeedbackModalVariant('override')
        }, 1500)
      } else {
        throw new Error(data?.detail || 'Failed to submit feedback')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setFeedbackSending(false)
    }
  }

  const handleApproveRecommendation = async () => {
    if (!result) return
    setFeedbackSending(true)
    try {
      const { ok, data } = await submitFeedback({
        request_id: result.request_id,
        predicted_class: result.predicted_class,
        clinician_action: 'approved',
        actual_dose_units: null,
        override_reason: '',
        input_summary: buildBody(form),
      })
      if (ok) {
        setToastMessage('Recommendation approved and recorded.')
        setToastShow(true)
      } else {
        throw new Error(data?.detail || 'Failed to record approval')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setFeedbackSending(false)
    }
  }

  return (
    <div className="dashboard">
      <section className="dashboard-section dashboard-patient-entry">
        <div className="card card-patient-selector">
          <label className="form-field">
            <span className="form-field-label">Patient *</span>
            <select
              className="form-select"
              value={selectedPatientId ?? ''}
              onChange={(e) => setSelectedPatientId(e.target.value ? Number(e.target.value) : null)}
              required
            >
              <option value="">— Select patient —</option>
              {(patients || []).map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.condition})</option>
              ))}
            </select>
          </label>
          {(!patients || patients.length === 0) && (
            <p className="card-description" style={{ marginTop: '0.5rem', marginBottom: 0 }}>
              No patients registered. <Link to={`${WORKSPACE_PATH}/patients`} style={{ color: 'var(--primary)', fontWeight: 500 }}>Register a patient</Link> first.
            </p>
          )}
        </div>
        <AssessmentForm
          form={form}
          fieldErrors={fieldErrors}
          quickEntryMode={quickEntryMode}
          recentMetrics={recentMetrics}
          patientRecentActivity={patientRecentActivity}
          loading={loading}
          onChange={handleChange}
          onQuickEntryChange={handleQuickEntryChange}
          onSubmit={getRecommendation}
        />
      </section>

      {error && (
        <div className="alert alert-warning" role="alert">{error}</div>
      )}

      {result && (
        <RecommendationResult
          result={result}
          form={form}
          reviewSubmitting={feedbackSending}
          onAdministerDose={() => setConfirmDoseOpen(true)}
          onApproveRecommendation={handleApproveRecommendation}
          onRejectRecommendation={() => {
            setFeedbackModalVariant('reject')
            setFeedbackOpen(true)
          }}
          onOverrideRecommendation={() => {
            setFeedbackModalVariant('override')
            setFeedbackOpen(true)
          }}
          onOpenResource={openResource}
        />
      )}

      {!result && !loading && (
        <div className="card card-empty-state">
          <p>Enter patient data above and select <strong>Get recommendation</strong> to see insulin guidance and trends.</p>
        </div>
      )}

      <ConfirmDoseModal
        open={confirmDoseOpen}
        onClose={() => setConfirmDoseOpen(false)}
        onConfirm={handleConfirmDose}
        doseSummary={doseSummary}
        loading={doseAdministering}
      />
      <SuccessToast message={toastMessage} show={toastShow} onDismiss={() => setToastShow(false)} />
      <ResourcePanel open={resourcePanelOpen} onClose={() => setResourcePanelOpen(false)} resourceId={resourceId} />
      <FeedbackModal
        open={feedbackOpen}
        variant={feedbackModalVariant}
        onClose={() => {
          setFeedbackOpen(false)
          setFeedbackModalVariant('override')
        }}
        onSubmit={handleFeedbackSubmit}
        loading={feedbackSending}
        success={feedbackSent}
      />
    </div>
  )
}
