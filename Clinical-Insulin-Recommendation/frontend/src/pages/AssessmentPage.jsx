/**
 * Assessment: patient selection, current assessment form, and recommendation results.
 */
import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useClinical } from '../context/ClinicalContext'
import ConfirmDoseModal from '../components/ConfirmDoseModal'
import SuccessToast from '../components/SuccessToast'
import ResourcePanel from '../components/ResourcePanel'
import FeedbackModal from '../components/FeedbackModal'
import AssessmentForm from '../components/dashboard/AssessmentForm'
import RecommendationResult from '../components/dashboard/RecommendationResult'
import PatientSearchCombobox from '../components/PatientSearchCombobox'
import { fetchRecommendation, recordDose, submitFeedback } from '../services/dashboardApi'
import {
  validateForm,
  buildBody,
  initialForm,
  DEFAULT_AGE,
  ageFromDateOfBirth,
  normalizeGenderForAssessment,
} from '../utils/assessmentFormUtils'
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
  const [feedbackSending, setFeedbackSending] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [quickEntryMode, setQuickEntryMode] = useState(false)
  const lastPrefilledPatientId = useRef(null)

  /** When the selected patient changes (or their row first loads), fill age from DOB and gender from registration. */
  useEffect(() => {
    if (!selectedPatientId) {
      lastPrefilledPatientId.current = null
      return
    }
    if (lastPrefilledPatientId.current === selectedPatientId) return

    const p = (patients || []).find(
      (x) => x.id === selectedPatientId || String(x.id) === String(selectedPatientId),
    )
    if (!p) return

    const ageVal = ageFromDateOfBirth(p.date_of_birth)
    const genderVal = normalizeGenderForAssessment(p.gender)

    lastPrefilledPatientId.current = selectedPatientId
    setForm((prev) => ({
      ...prev,
      age: ageVal != null ? String(ageVal) : prev.age,
      gender: genderVal != null ? genderVal : prev.gender,
    }))
  }, [selectedPatientId, patients])

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
          age: form.age != null && form.age !== '' ? form.age : DEFAULT_AGE,
          gender: form.gender || 'Male',
          food_intake: 'Medium',
          previous_medications: 'None',
          glucose_level: form.glucose_level,
          measurement_time: form.measurement_time || initialForm().measurement_time,
          meal_context: form.meal_context || 'fasting',
          activity_context: form.activity_context || 'resting',
          iob: form.iob,
          anticipated_carbs: form.anticipated_carbs,
          glucose_trend: form.glucose_trend,
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
            age: form.age != null && form.age !== '' ? form.age : DEFAULT_AGE,
            gender: form.gender || 'Male',
            food_intake: 'Medium',
            previous_medications: 'None',
            glucose_level: form.glucose_level,
            measurement_time: form.measurement_time || initialForm().measurement_time,
            meal_context: form.meal_context || 'fasting',
            activity_context: form.activity_context || 'resting',
            iob: form.iob,
            anticipated_carbs: form.anticipated_carbs,
            glucose_trend: form.glucose_trend,
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
        setTimeout(() => { setFeedbackOpen(false); setFeedbackSent(false) }, 1500)
      } else {
        throw new Error(data?.detail || 'Failed to submit feedback')
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
          <label className="form-field" htmlFor="assessment-patient-search">
            <span className="form-field-label">Patient *</span>
            <PatientSearchCombobox
              id="assessment-patient-search"
              patients={patients || []}
              value={selectedPatientId}
              onChange={(id) => setSelectedPatientId(id == null ? null : Number(id))}
              placeholder={(!patients || patients.length === 0) ? 'Register a patient first…' : 'Search by name or ID…'}
            />
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
          onAdministerDose={() => setConfirmDoseOpen(true)}
          onReportOverride={() => setFeedbackOpen(true)}
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
      <SuccessToast message="Dose recorded successfully." show={toastShow} onDismiss={() => setToastShow(false)} />
      <ResourcePanel open={resourcePanelOpen} onClose={() => setResourcePanelOpen(false)} resourceId={resourceId} />
      <FeedbackModal
        open={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        onSubmit={handleFeedbackSubmit}
        loading={feedbackSending}
        success={feedbackSent}
      />
    </div>
  )
}
