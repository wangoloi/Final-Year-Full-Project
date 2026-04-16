import { useClinical } from '../context/ClinicalContext'

export default function ApiErrorBanner() {
  const { apiError, clearApiError } = useClinical()
  if (!apiError?.message) return null

  return (
    <div className="api-error-banner" role="alert" aria-live="polite">
      <div className="api-error-banner__body">
        <strong className="api-error-banner__title">Connection issue</strong>
        <span className="api-error-banner__text">{apiError.message}</span>
      </div>
      <button
        type="button"
        className="api-error-banner__dismiss"
        onClick={clearApiError}
        aria-label="Dismiss"
        title="Dismiss"
      >
        ×
      </button>
    </div>
  )
}

