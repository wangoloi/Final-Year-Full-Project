/**
 * Embedded Glocusense meal plan — loaded only from workspace nav (not on Dashboard home).
 */
import { useRef, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useMealPlanSsoBridge } from '../components/MealPlanSsoBridge'
import { getMealPlanAppUrl, WORKSPACE_PATH } from '../constants'

export default function MealPlanEmbedPage() {
  const mealIframeRef = useRef(null)
  const { onIframeLoad: onMealIframeLoad, ssoError, dismissSsoError } = useMealPlanSsoBridge(mealIframeRef)
  const iframeSrc = useMemo(() => getMealPlanAppUrl({ embed: true }), [])

  return (
    <div className="dashboard">
      <section className="dashboard-section dashboard-meal-plan-embed" aria-labelledby="meal-plan-embed-heading">
        <div className="card">
          {ssoError && (
            <div className="alert alert-warning meal-plan-sso-banner" role="alert">
              <div className="meal-plan-sso-banner__row">
                <div>
                  <strong>Connection issue</strong>
                  <p className="meal-plan-sso-banner__msg">{ssoError}</p>
                </div>
                <button type="button" className="meal-plan-sso-banner__dismiss" onClick={dismissSsoError} aria-label="Dismiss">
                  ×
                </button>
              </div>
            </div>
          )}
          <h2 id="meal-plan-embed-heading" className="dashboard-meal-plan-title">Meal plan (Glocusense)</h2>
          <p className="card-description" style={{ marginTop: 0 }}>
            Embedded meal-planning app for the same patient journey. Run the Meal Plan dev server and set{' '}
            <code>VITE_MEAL_PLAN_URL</code> if it is not on the default port.
          </p>
          <div className="meal-plan-embed-frame-wrap">
            <iframe
              ref={mealIframeRef}
              title="Glocusense meal plan"
              src={iframeSrc}
              className="meal-plan-embed-iframe"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              onLoad={onMealIframeLoad}
            />
          </div>
          <p className="card-description" style={{ marginBottom: 0 }}>
            <Link to="/meal-plan">Open meal plan full screen</Link>
            {' · '}
            <Link to={WORKSPACE_PATH}>Back to dashboard</Link>
          </p>
        </div>
      </section>
    </div>
  )
}
