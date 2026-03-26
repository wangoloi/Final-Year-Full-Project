import { useEffect } from 'react'

export default function ConfirmDoseModal({ open, onClose, onConfirm, doseSummary, loading }) {
  useEffect(() => {
    if (!open) return
    const handle = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handle)
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', handle); document.body.style.overflow = '' }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="confirm-dose-title">
      <div className="modal-card confirm-dose-modal" onClick={(e) => e.stopPropagation()}>
        <h2 id="confirm-dose-title" className="modal-title">Confirm dose administration</h2>
        <p className="modal-description">Verify the following before administering to the patient.</p>
        {doseSummary && (
          <div className="confirm-dose-summary">
            <div className="confirm-dose-row"><span>Meal bolus</span><strong>{doseSummary.mealBolus ?? '—'}</strong></div>
            <div className="confirm-dose-row"><span>Correction dose</span><strong>{doseSummary.correctionDose ?? '—'}</strong></div>
            <div className="confirm-dose-row confirm-dose-total"><span>Total dose</span><strong>{doseSummary.totalDose ?? '—'}</strong></div>
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={onConfirm} disabled={loading}>
            {loading ? 'Recording…' : 'Administer dose'}
          </button>
        </div>
      </div>
    </div>
  )
}
