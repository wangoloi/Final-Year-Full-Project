/**
 * Assessment form for patient data entry.
 * Single responsibility: render form fields and validation errors.
 */
import {
  AGE_MIN, AGE_MAX, GENDER_OPTIONS,
  GLUCOSE_MIN, GLUCOSE_MAX, BMI_MIN, BMI_MAX, HBA1C_MIN, HBA1C_MAX, WEIGHT_MIN, WEIGHT_MAX,
  MEAL_CONTEXT_OPTIONS, ACTIVITY_CONTEXT_OPTIONS,
} from '../../constants'
import { NUMERIC_FIELDS } from '../../utils/assessmentFormUtils'

export default function AssessmentForm({
  form,
  fieldErrors,
  quickEntryMode,
  recentMetrics,
  patientRecentActivity,
  loading,
  onChange,
  onQuickEntryChange,
  onSubmit,
}) {
  const handleChange = (key, value) => {
    if (key === '_quickEntry') {
      onQuickEntryChange?.(value)
      return
    }
    onChange(key, value)
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <div>
          <h2 className="card-heading">Current assessment</h2>
          <p className="card-description">
            Enter patient data below. Click Get recommendation to run the current assessment.
          </p>
        </div>
        <label className="form-quick-entry">
          <input
            type="checkbox"
            checked={quickEntryMode}
            onChange={(e) => handleChange('_quickEntry', e.target.checked)}
            aria-label="Quick entry mode"
          />
          <span>Quick check (glucose only)</span>
        </label>
      </div>

      {fieldErrors.length > 0 && (
        <ul className="form-validation-errors" role="alert" aria-live="polite">
          {fieldErrors.map((err, i) => (
            <li key={i} data-field={err.field}>
              <strong>{err.field}:</strong> {err.message}
            </li>
          ))}
        </ul>
      )}

      <div className="form-grid">
        <SmartSensorContextFields form={form} fieldErrors={fieldErrors} onChange={handleChange} />
        {!quickEntryMode && (
          <>
            <FormFieldAge form={form} fieldErrors={fieldErrors} onChange={handleChange} />
            <FormFieldGender form={form} fieldErrors={fieldErrors} onChange={handleChange} />
          </>
        )}
        <FormFieldGlucose form={form} fieldErrors={fieldErrors} quickEntryMode={quickEntryMode} recentMetrics={recentMetrics} onChange={handleChange} />
        {!quickEntryMode && NUMERIC_FIELDS.filter((f) => f.key !== 'glucose_level').map(({ key, label }) => (
          <FormFieldNumeric
            key={key}
            fieldKey={key}
            label={label}
            form={form}
            fieldErrors={fieldErrors}
            min={key === 'BMI' ? BMI_MIN : key === 'HbA1c' ? HBA1C_MIN : key === 'weight' ? WEIGHT_MIN : undefined}
            max={key === 'BMI' ? BMI_MAX : key === 'HbA1c' ? HBA1C_MAX : key === 'weight' ? WEIGHT_MAX : undefined}
            onChange={handleChange}
          />
        ))}
        <RecentPatientActivityPanel recent={patientRecentActivity} />
      </div>

      <button type="button" className="btn btn-primary" onClick={onSubmit} disabled={loading}>
        {loading ? 'Getting recommendation…' : 'Get recommendation'}
      </button>
    </div>
  )
}

function formatTs(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return String(ts)
  return d.toLocaleString()
}

function RecentPatientActivityPanel({ recent }) {
  const lastGlucose = recent?.last_glucose
  const lastDose = recent?.last_dose
  const lastRec = recent?.last_recommendation
  const lastRecSummary = lastRec?.recommendation_summary || lastRec?.recommended_action || ''
  const lastRecSaysNoInsulin = String(lastRec?.dosage_action || '').toLowerCase() === 'none'
  return (
    <div className="form-field form-field-full" style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
      <span className="form-label" style={{ fontWeight: 600 }}>Recent patient activity</span>
      <p className="form-hint" style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
        Shows the most recent glucose reading and recorded insulin injection for the selected patient.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
        <div style={{ padding: '0.75rem', border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Last glucose</div>
          <div style={{ fontWeight: 700, fontSize: '1rem' }}>
            {lastGlucose?.value != null ? `${lastGlucose.value} mg/dL` : '—'}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {formatTs(lastGlucose?.reading_at)}
          </div>
        </div>
        <div style={{ padding: '0.75rem', border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Last insulin dose injected</div>
          <div style={{ fontWeight: 700, fontSize: '1rem' }}>
            {lastRecSaysNoInsulin
              ? 'No insulin used'
              : (lastDose?.total_dose != null && String(lastDose.total_dose).trim() ? String(lastDose.total_dose) : '—')}
          </div>
          {lastRecSaysNoInsulin && lastRecSummary && (
            <div style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Advice:</span> {lastRecSummary}
            </div>
          )}
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {lastRecSaysNoInsulin ? formatTs(lastRec?.created_at) : formatTs(lastDose?.created_at)}
          </div>
        </div>
      </div>
    </div>
  )
}

function SmartSensorContextFields({ form, fieldErrors, onChange }) {
  const tErr = fieldErrors.find((e) => e.field === 'measurement_time')
  const mErr = fieldErrors.find((e) => e.field === 'meal_context')
  const aErr = fieldErrors.find((e) => e.field === 'activity_context')
  return (
    <>
      <div className="form-field form-field-full" style={{ gridColumn: '1 / -1' }}>
        <span className="form-label" style={{ fontWeight: 600 }}>Measurement context (required)</span>
        <p className="form-hint" style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
          Used by the Smart Sensor model for time-aware features (sin/cos clock, meal and activity context).
        </p>
      </div>
      <label className="form-field">
        <span className="form-label">Measurement date &amp; time *</span>
        <input
          type="datetime-local"
          value={form.measurement_time ?? ''}
          onChange={(e) => onChange('measurement_time', e.target.value)}
          className="form-input"
          aria-invalid={!!tErr}
        />
        {tErr && <span className="form-field-error">{tErr.message}</span>}
      </label>
      <label className="form-field">
        <span className="form-label">Meal context *</span>
        <select
          value={form.meal_context ?? 'fasting'}
          onChange={(e) => onChange('meal_context', e.target.value)}
          className="form-input form-select"
          aria-invalid={!!mErr}
        >
          {MEAL_CONTEXT_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>{opt.replace(/_/g, ' ')}</option>
          ))}
        </select>
        {mErr && <span className="form-field-error">{mErr.message}</span>}
      </label>
      <label className="form-field">
        <span className="form-label">Activity context *</span>
        <select
          value={form.activity_context ?? 'resting'}
          onChange={(e) => onChange('activity_context', e.target.value)}
          className="form-input form-select"
          aria-invalid={!!aErr}
        >
          {ACTIVITY_CONTEXT_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>{opt.replace(/_/g, ' ')}</option>
          ))}
        </select>
        {aErr && <span className="form-field-error">{aErr.message}</span>}
      </label>
    </>
  )
}

function FormFieldAge({ form, fieldErrors, onChange }) {
  const err = fieldErrors.find((e) => e.field === 'age')
  return (
    <label className="form-field">
      <span className="form-label">Age (years) *</span>
      <input
        type="number"
        min={AGE_MIN}
        max={AGE_MAX}
        step="1"
        value={form.age ?? ''}
        onChange={(e) => onChange('age', e.target.value)}
        className="form-input"
        aria-invalid={!!err}
        aria-describedby={err ? 'age-error' : undefined}
      />
      {err && <span id="age-error" className="form-field-error">{err.message}</span>}
    </label>
  )
}

function FormFieldGender({ form, fieldErrors, onChange }) {
  const err = fieldErrors.find((e) => e.field === 'gender')
  return (
    <label className="form-field">
      <span className="form-label">Gender *</span>
      <select value={form.gender ?? ''} onChange={(e) => onChange('gender', e.target.value)} className="form-input form-select" aria-invalid={!!err}>
        <option value="">Select...</option>
        {GENDER_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
      </select>
      {err && <span className="form-field-error">{err.message}</span>}
    </label>
  )
}

function FormFieldGlucose({ form, fieldErrors, quickEntryMode, recentMetrics, onChange }) {
  const err = fieldErrors.find((e) => e.field === 'glucose_level')
  return (
    <label className="form-field">
      <span className="form-label">Glucose (mg/dL) *</span>
      <input
        type="number"
        step="any"
        min={GLUCOSE_MIN}
        max={GLUCOSE_MAX}
        value={form.glucose_level ?? ''}
        onChange={(e) => onChange('glucose_level', e.target.value)}
        className="form-input"
        aria-invalid={!!err}
        aria-describedby={err ? 'glucose-error' : undefined}
      />
      {err && <span id="glucose-error" className="form-field-error" role="alert">{err.message}</span>}
      {quickEntryMode && recentMetrics?.glucose != null && (
        <span className="form-hint" style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>Last: {recentMetrics.glucose} mg/dL</span>
      )}
    </label>
  )
}

function FormFieldNumeric({ fieldKey, label, form, fieldErrors, min, max, onChange }) {
  const err = fieldErrors.find((e) => e.field === fieldKey)
  return (
    <label className="form-field">
      <span className="form-label">{label}</span>
      <input
        type="number"
        step="any"
        min={min}
        max={max}
        value={form[fieldKey] ?? ''}
        onChange={(e) => onChange(fieldKey, e.target.value)}
        className="form-input"
        aria-invalid={!!err}
        aria-describedby={err ? `${fieldKey}-error` : undefined}
      />
      {err && <span id={`${fieldKey}-error`} className="form-field-error" role="alert">{err.message}</span>}
    </label>
  )
}

// Type 1 dosing context UI removed (replaced by RecentPatientActivityPanel)
