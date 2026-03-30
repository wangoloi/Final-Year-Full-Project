/**
 * Recommendation result display.
 * Single responsibility: render recommendation cards and actions.
 */
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
  onReportOverride,
  onOpenResource,
}) {
  const clinicalSummary = CLINICAL_LABELS[result.predicted_class] || result.recommendation_summary
  const confidence = Math.round((result.confidence || 0) * 100)
  const isCaution = result.is_high_risk || confidence < CONFIDENCE_CAUTION_THRESHOLD_PCT
  const certaintyTier = confidence >= CONFIDENCE_HIGH_PCT ? 'High' : confidence >= CONFIDENCE_MEDIUM_PCT ? 'Medium' : 'Low'
  return (
    <>
      <section className="dashboard-section dashboard-insight-row">
        <CurrentReadingCard result={result} form={form} />
        <InsulinRecommendationCard result={result} clinicalSummary={clinicalSummary} confidence={confidence} isCaution={isCaution} certaintyTier={certaintyTier} />
        <DosageGuidanceCard result={result} onAdminister={onAdministerDose} onReportOverride={onReportOverride} />
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
    </>
  )
}

function CurrentReadingCard({ result, form }) {
  return (
    <div className="card card-ui-recommendation" style={{ gridColumn: '1 / -1' }}>
      <h2 className="card-heading">Current reading</h2>
      <dl className="ui-recommendation-dl">
        <dt>Current Reading</dt>
        <dd>{result.current_reading_display || `${form.glucose_level || '—'} mg/dL`}</dd>
        <dt>Trend</dt>
        <dd>{result.trend_display || '—'}</dd>
        <dt>IOB</dt>
        <dd>{result.iob_display || 'Not provided'}</dd>
        <dt>What the readings suggest</dt>
        <dd className="ui-interpretation">{result.system_interpretation || result.context_summary || result.recommendation_summary}</dd>
      </dl>
    </div>
  )
}

function InsulinRecommendationCard({ result, clinicalSummary, confidence, isCaution, certaintyTier }) {
  return (
    <div className="card card-insight recommendation-card">
      <h2 className="card-heading">Insulin recommendation</h2>
      <div className={`recommendation-insight ${isCaution ? 'recommendation-caution' : ''}`}>
        <div className="recommendation-value">{clinicalSummary}</div>
        <div className="recommendation-confidence" title={CERTAINTY_TOOLTIP}>
          <span className="confidence-label">
            Certainty
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
        <p className="recommendation-tooltip" title={result.recommendation_detail}>
          {result.recommendation_summary}
        </p>
      </div>
    </div>
  )
}

function DosageGuidanceCard({ result, onAdminister, onReportOverride }) {
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
      <button type="button" className="btn btn-primary btn-administer" onClick={onAdminister}>
        Administer dose
      </button>
      <button type="button" className="btn btn-secondary" style={{ marginTop: '0.5rem', marginLeft: '0.5rem' }} onClick={onReportOverride}>
        Report override
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
