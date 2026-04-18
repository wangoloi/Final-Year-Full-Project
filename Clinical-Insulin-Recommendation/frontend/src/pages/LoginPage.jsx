import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useClinical } from '../context/ClinicalContext'
import { WORKSPACE_PATH, getPublicSiteHostname, getMealPlanOrigin } from '../constants'
import BrandLogo from '../components/BrandLogo'

function sanitizeNextPath(raw) {
  if (raw == null || typeof raw !== 'string') return null
  const s = raw.trim()
  if (!s.startsWith('/') || s.startsWith('//') || s.includes('..')) return null
  return s
}

/**
 * Optional: link a Meal Plan account for SSO into the nutrition iframe.
 * GlucoSense clinical workspace does not require this — open /workspace directly.
 */
export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { loginWithMealPlan } = useClinical()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  const mealOrigin = getMealPlanOrigin()
  const mealRegisterUrl = `${mealOrigin}/register`
  const mealLoginUrl = `${mealOrigin}/login`

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setPending(true)
    try {
      await loginWithMealPlan(email.trim(), password)
      const next = sanitizeNextPath(searchParams.get('next'))
      navigate(next || WORKSPACE_PATH, { replace: true })
    } catch (err) {
      setError(err?.message || 'Link failed')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="unified-login">
      <div className="unified-login-card">
        <Link to={WORKSPACE_PATH} className="unified-login-back">
          ← Clinical workspace
        </Link>
        <div className="unified-login-logo">
          <BrandLogo size={48} />
        </div>
        <h1>Link Meal Plan account</h1>
        <p className="unified-login-host">{getPublicSiteHostname()}</p>
        <p className="unified-login-lead">
          Optional: sign in with your <strong>Meal Plan</strong> credentials to sync the nutrition app in the iframe
          (single sign-on). The <strong>clinical workspace</strong> does not require this — use{' '}
          <Link to={WORKSPACE_PATH}>Clinical workspace</Link> anytime without logging in here.
        </p>

        <div className="unified-login-choice" role="group" aria-label="Meal Plan account options">
          <a href={mealRegisterUrl} className="unified-login-choice-link unified-login-choice-link--primary">
            Create Meal Plan account
          </a>
          <span className="unified-login-choice-sep" aria-hidden>
            ·
          </span>
          <a href={mealLoginUrl} className="unified-login-choice-link">
            Meal Plan sign-in (standalone)
          </a>
        </div>

        <form className="unified-login-form" onSubmit={handleSubmit}>
          <label className="unified-field">
            <span>Email or username</span>
            <input
              type="text"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Meal Plan account"
              required
            />
          </label>
          <label className="unified-field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </label>

          {error ? (
            <p className="unified-login-error" role="alert">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            className="unified-btn unified-btn-primary unified-btn-block"
            disabled={pending}
          >
            {pending ? 'Linking…' : 'Link account'}
          </button>
        </form>

        <p className="unified-login-hint">
          Login is required only inside the <strong>Meal Plan</strong> app when you use nutrition features there
          directly (port 5175). GlucoSense clinical tools use the local API without Meal Plan credentials.
        </p>
      </div>
    </div>
  )
}
