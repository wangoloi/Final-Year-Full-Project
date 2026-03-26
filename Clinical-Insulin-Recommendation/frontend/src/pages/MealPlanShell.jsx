import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { FiActivity, FiLogOut } from 'react-icons/fi'
import { useClinical } from '../context/ClinicalContext'
import { useMealPlanSsoBridge } from '../components/MealPlanSsoBridge'
import { WORKSPACE_PATH, getMealPlanAppUrl } from '../constants'

/**
 * Embedded Glocusense Meal Plan (separate Vite app).
 * SSO: one GlucoSense login provisions a Meal Plan JWT and posts it into the iframe (no second login).
 */
export default function MealPlanShell() {
  const { userRole, setSignedIn, userProfile } = useClinical()
  const iframeRef = useRef(null)
  const { onIframeLoad } = useMealPlanSsoBridge(iframeRef)
  const iframeSrc = getMealPlanAppUrl({ embed: true })

  return (
    <div className="meal-plan-shell">
      <header className="meal-plan-shell-header">
        <div className="meal-plan-shell-brand">
          <FiActivity size={22} aria-hidden />
          <div>
            <span className="meal-plan-shell-title">GlucoSense</span>
            <span className="meal-plan-shell-sub">Meal plan & nutrition</span>
          </div>
        </div>
        <div className="meal-plan-shell-actions">
          {userProfile?.displayName && (
            <span className="meal-plan-shell-user">{userProfile.displayName}</span>
          )}
          {userRole === 'clinician' && (
            <Link to={WORKSPACE_PATH} className="meal-plan-shell-link">
              Clinical dashboard
            </Link>
          )}
          <button
            type="button"
            className="meal-plan-shell-logout"
            onClick={() => {
              setSignedIn(false)
              window.location.href = '/'
            }}
          >
            <FiLogOut size={18} aria-hidden />
            Sign out
          </button>
        </div>
      </header>
      <div className="meal-plan-shell-frame-wrap">
        <iframe
          ref={iframeRef}
          title="Glocusense Meal Plan"
          src={iframeSrc}
          className="meal-plan-shell-iframe"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          onLoad={onIframeLoad}
        />
      </div>
      <p className="meal-plan-shell-note">
        If this area is blank, start the Meal Plan API on port <strong>8001</strong> and its Vite app (integrated
        setup uses <strong>5175</strong>), and set <code>VITE_MEAL_PLAN_URL</code> /{' '}
        <code>VITE_MEAL_PLAN_API_URL</code> in GlucoSense if your ports differ.
      </p>
    </div>
  )
}
