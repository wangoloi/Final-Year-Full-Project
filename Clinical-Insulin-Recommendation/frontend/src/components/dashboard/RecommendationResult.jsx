/**
 * Recommendation result display.
 * Single responsibility: render recommendation cards and actions.
 */
import { RISK_LABELS } from '../FeedbackModal'
import {
  CONFIDENCE_CAUTION_THRESHOLD_PCT,
  CONFIDENCE_HIGH_PCT,
  CONFIDENCE_MEDIUM_PCT,
  EXPLANATION_DRIVERS_DISPLAY_LIMIT,
  CERTAINTY_TOOLTIP,
} from '../../constants'

const CLINICAL_LABELS = {
  down: 'Consider decrease',
  up: 'Consider increase',
  steady: 'Maintain current dose',
  no: 'No change',
}

export default function RecommendationResult({
  result,
  form,
  onAdministerDose,
  onApproveRecommendation,
  onRejectRecommendation,
  onOverrideRecommendation,
  reviewSubmitting,
  onOpenResource,
}) {
  const clinicalSummary = CLINICAL_LABELS[result.predicted_class] || result.recommendation_summary
  const confidence = Math.round((result.confidence || 0) * 100)
  const isCaution = result.is_high_risk || confidence < CONFIDENCE_CAUTION_THRESHOLD_PCT
  const certaintyTier = confidence >= CONFIDENCE_HIGH_PCT ? 'High' : confidence >= CONFIDENCE_MEDIUM_PCT ? 'Medium' : 'Low'
  return (
    <>
      <section className="dashboard-section" aria-label="Primary action">
        <PrimaryActionCard result={result} />
      </section>

      {result.risk_flags?.length > 0 && (
        <RiskFlagsCard riskFlags={result.risk_flags} />
      )}

      <section className="dashboard-section dashboard-insight-row">
        <CurrentReadingCard result={result} form={form} />
        <InsulinRecommendationCard result={result} clinicalSummary={clinicalSummary} isCaution={isCaution} />
        <DosageGuidanceCard result={result} />
      </section>

      <section className="dashboard-section dashboard-advice-row">
        <AdjustmentAdviceCard result={result} />
        <ContributingFactorsCard result={result} />
      </section>

      <section className="dashboard-section">
        <h2 className="section-heading">Clinical resources</h2>
        <ResourcesGrid onOpenResource={onOpenResource} />
      </section>

      <div className="card card-disclaimer">
        <p className="disclaimer-text">{result.clinical_disclaimer}</p>
      </div>

      <section className="dashboard-section clinical-review-section" aria-label="Review and confirm">
        <ClinicalReviewPanel
          result={result}
          confidence={confidence}
          certaintyTier={certaintyTier}
          isCaution={isCaution}
          reviewSubmitting={reviewSubmitting}
          onApprove={onApproveRecommendation}
          onReject={onRejectRecommendation}
          onOverride={onOverrideRecommendation}
          onAdministerDose={onAdministerDose}
        />
      </section>
    </>
  )
}

function PrimaryActionCard({ result }) {
  return (
    <div className={`card card-primary-action ${result.is_high_risk ? 'card-primary-action--critical' : ''}`}>
      <h2 className="card-heading" style={{ marginBottom: '0.5rem' }}>Recommended action</h2>
      <p className="primary-action-text" role="status">
        {result.recommended_action || result.recommendation_summary}
      </p>
      {result.is_high_risk && (
        <p className="primary-action-note" style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--chart-low)' }}>
          {result.high_risk_reason}
        </p>
      )}
    </div>
  )
}

function RiskFlagsCard({ riskFlags }) {
  return (
    <div className="alert alert-critical" role="alert" style={{ marginBottom: '1rem', borderLeft: '4px solid #c62828', padding: '1rem', background: 'rgba(198, 40, 40, 0.08)', borderRadius: 8 }}>
      <strong>Risk flags:</strong>
      <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem' }}>
        {riskFlags.map((f, i) => (
          <li key={i}>{RISK_LABELS[f] || f}</li>
        ))}
      </ul>
    </div>
  )
}

function CurrentReadingCard({ result, form }) {
  return (
    <div className="card card-ui-recommendation" style={{ gridColumn: '1 / -1' }}>
      <h2 className="card-heading">Current reading</h2>
      <dl className="ui-recommendation-dl">
        <dt>Current Reading</dt>
        <dd>{result.current_reading_display || `${form.glucose_level || '—'} mg/dL`}</dd>
        <dt>What the readings suggest</dt>
        <dd className="ui-interpretation">{result.system_interpretation || result.context_summary || result.recommendation_summary}</dd>
        <dt>Recommended Action</dt>
        <dd className="ui-action"><strong>{result.recommended_action || result.recommendation_summary}</strong></dd>
      </dl>
    </div>
  )
}

function InsulinRecommendationCard({ result, clinicalSummary, isCaution }) {
  return (
    <div className="card card-insight recommendation-card">
      <h2 className="card-heading">Insulin recommendation</h2>
      <div className={`recommendation-insight ${isCaution ? 'recommendation-caution' : ''}`}>
        <div className="recommendation-value">{clinicalSummary}</div>
        <p className="recommendation-tooltip" title={result.recommendation_detail}>
          {result.recommendation_summary}
        </p>
      </div>
    </div>
  )
}

function DosageGuidanceCard({ result }) {
  return (
    <div className="card card-insight dosage-card">
      <h2 className="card-heading">Dosage guidance</h2>
      <div className="dosage-breakdown">
        <div className="dosage-row">
          <span>Meal bolus</span>
          <strong>{result.dosage_magnitude || 'Per protocol'}</strong>
        </div>
        <div className="dosage-row">
          <span>Correction dose</span>
          <strong>{result.dosage_action || '—'}</strong>
        </div>
        <div className="dosage-row dosage-row-total">
          <span>Total dose</span>
          <strong>{result.recommendation_summary || 'See above'}</strong>
        </div>
      </div>
      <p className="text-muted" style={{ margin: 0, fontSize: '0.85rem' }}>
        Use <strong>Review &amp; confirm</strong> below to record certainty, your decision, and dose actions.
      </p>
    </div>
  )
}

function ClinicalReviewPanel({
  result,
  confidence,
  certaintyTier,
  isCaution,
  reviewSubmitting,
  onApprove,
  onReject,
  onOverride,
  onAdministerDose,
}) {
  return (
    <div className="card card-clinical-review">
      <h2 className="card-heading">Review &amp; confirm</h2>
      <p className="card-description" style={{ marginBottom: '1rem' }}>
        After reviewing the guidance above, check model certainty, then record whether you accept this assessment, reject it, or need to override it. Administering a dose remains a separate step.
      </p>
      <div className={`clinical-review-certainty ${isCaution ? 'clinical-review-certainty--caution' : ''}`} title={CERTAINTY_TOOLTIP}>
        <span className="confidence-label">
          Model certainty
          <span className={`confidence-tier confidence-tier--${certaintyTier.toLowerCase()}`}>({certaintyTier})</span>
        </span>
        <div className="confidence-bar">
          <div className="confidence-fill" style={{ width: `${confidence}%` }} />
        </div>
        <span className="confidence-pct">{confidence}%</span>
        {certaintyTier === 'Low' && (
          <p className="confidence-note">Multiple options are plausible—use clinical judgment.</p>
        )}
      </div>
      <div className="clinical-review-actions" role="group" aria-label="Clinical decision">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={reviewSubmitting}
          onClick={() => onApprove?.(result)}
        >
          {reviewSubmitting ? 'Recording…' : 'Approve'}
        </button>
        <button
          type="button"
          className="btn btn-secondary clinical-review-btn-reject"
          disabled={reviewSubmitting}
          onClick={() => onReject?.(result)}
        >
          Reject
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={reviewSubmitting}
          onClick={() => onOverride?.(result)}
        >
          Override
        </button>
      </div>
      <button
        type="button"
        className="btn btn-primary btn-administer clinical-review-administer"
        disabled={reviewSubmitting}
        onClick={onAdministerDose}
      >
        Administer dose
      </button>
    </div>
  )
}

function AdjustmentAdviceCard({ result }) {
  return (
    <div className="card card-advice">
      <h2 className="card-heading">Adjustment advice</h2>
      <div className={`advice-content ${result.is_high_risk ? 'advice-caution' : ''}`}>
        <p>{result.recommendation_summary}</p>
        {result.context_summary && (
          <p className="advice-context" style={{ fontWeight: 500, marginTop: '0.5rem', padding: '0.5rem', background: 'var(--surface)', borderRadius: 6 }}>
            <strong>Context summary:</strong> {result.context_summary}
          </p>
        )}
        {result.recommendation_detail && <p className="advice-detail">{result.recommendation_detail}</p>}
        {result.is_high_risk && (
          <div className="advice-flag">
            <strong>Flag for review:</strong> {result.high_risk_reason || 'System less certain than usual.'}
          </div>
        )}
      </div>
    </div>
  )
}

function ContributingFactorsCard({ result }) {
  const drivers = result.explanation_drivers || []
  return (
    <div className="card card-factors">
      <h2 className="card-heading">Contributing factors</h2>
      {drivers.length > 0 ? (
        <ul className="factor-list">
          {drivers.slice(0, EXPLANATION_DRIVERS_DISPLAY_LIMIT).map((d, i) => (
            <li key={i}>{d.clinical_sentence || `${d.feature}: ${d.value}`}</li>
          ))}
        </ul>
      ) : (
        <p className="text-muted">Factors are based on current readings and protocol.</p>
      )}
    </div>
  )
}

function ResourcesGrid({ onOpenResource }) {
  const resources = [
    { id: 'hypo', title: 'Hypoglycemia protocol', desc: 'Recognition and treatment' },
    { id: 'diet', title: 'Dietary guidance', desc: 'Carb counting and meal planning' },
    { id: 'exercise', title: 'Exercise recommendations', desc: 'Activity and glucose' },
  ]
  return (
    <div className="resources-grid">
      {resources.map((r) => (
        <button key={r.id} type="button" className="resource-card" onClick={() => onOpenResource(r.id)}>
          <span className="resource-card-title">{r.title}</span>
          <span className="resource-card-desc">{r.desc}</span>
        </button>
      ))}
    </div>
  )
}
