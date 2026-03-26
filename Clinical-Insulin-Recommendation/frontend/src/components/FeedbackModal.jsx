import { useState, useEffect } from 'react'

const RISK_LABELS = {
  hypoglycemia_alert: 'Hypoglycemia alert',
  high_uncertainty: 'High uncertainty',
  cgm_error: 'CGM sensor error',
  high_ketones: 'High ketones',
}

export default function FeedbackModal({ open, onClose, onSubmit, loading, success }) {
  const [clinicianAction, setClinicianAction] = useState('')
  useEffect(() => {
    if (!open) return
    const handle = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handle)
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', handle); document.body.style.overflow = '' }
  }, [open, onClose])
  const [actualDoseUnits, setActualDoseUnits] = useState('')
  const [overrideReason, setOverrideReason] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ clinician_action: clinicianAction, actual_dose_units: actualDoseUnits, override_reason: overrideReason })
    setClinicianAction('')
    setActualDoseUnits('')
    setOverrideReason('')
  }

  if (!open) return null
  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="feedback-title">
      <div className="modal-card confirm-dose-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
        <h2 id="feedback-title" className="card-heading">Report clinician override</h2>
        <p className="card-description" style={{ marginBottom: '1rem' }}>
          Record when you override the system recommendation. This helps improve future models.
        </p>
        {success ? (
          <p className="text-success" style={{ fontWeight: 600 }}>Feedback recorded. Thank you.</p>
        ) : (
          <form onSubmit={handleSubmit}>
            <label className="form-field" style={{ display: 'block', marginBottom: '1rem' }}>
              <span className="form-label">Clinician action</span>
              <select
                value={clinicianAction}
                onChange={(e) => setClinicianAction(e.target.value)}
                className="form-input form-select"
                required
              >
                <option value="">Select...</option>
                <option value="increased">Increased dose</option>
                <option value="decreased">Decreased dose</option>
                <option value="maintained">Maintained (no change)</option>
                <option value="withheld">Withheld insulin</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label className="form-field" style={{ display: 'block', marginBottom: '1rem' }}>
              <span className="form-label">Actual dose (units, if applicable)</span>
              <input
                type="number"
                step="0.1"
                min="0"
                value={actualDoseUnits}
                onChange={(e) => setActualDoseUnits(e.target.value)}
                className="form-input"
                placeholder="e.g. 4.5"
              />
            </label>
            <label className="form-field" style={{ display: 'block', marginBottom: '1rem' }}>
              <span className="form-label">Override reason</span>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                className="form-input"
                rows={3}
                placeholder="Brief reason for override..."
              />
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={loading || !clinicianAction}>
                {loading ? 'Sending…' : 'Submit feedback'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export { RISK_LABELS }
