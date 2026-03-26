import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { FiActivity } from 'react-icons/fi'
import { useClinical } from '../context/ClinicalContext'
import { WORKSPACE_PATH } from '../constants'

export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, isSignedIn, userRole } = useClinical()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('clinician')

  useEffect(() => {
    const r = searchParams.get('role')
    if (r === 'patient' || r === 'clinician') setRole(r)
  }, [searchParams])

  useEffect(() => {
    if (!isSignedIn) return
    if (userRole === 'patient') navigate('/meal-plan', { replace: true })
    else if (userRole === 'clinician') navigate(WORKSPACE_PATH, { replace: true })
  }, [isSignedIn, userRole, navigate])

  const handleSubmit = (e) => {
    e.preventDefault()
    const displayName = email.split('@')[0] || (role === 'clinician' ? 'Clinician' : 'Patient')
    login(role, {
      email: email.trim(),
      displayName,
      role: role === 'clinician' ? 'Clinician' : 'Patient',
    })
    if (role === 'patient') navigate('/meal-plan', { replace: true })
    else navigate(WORKSPACE_PATH, { replace: true })
  }

  return (
    <div className="unified-login">
      <div className="unified-login-card">
        <Link to="/" className="unified-login-back">
          ← Home
        </Link>
        <div className="unified-login-logo">
          <FiActivity size={40} aria-hidden />
        </div>
        <h1>Sign in</h1>
        <p className="unified-login-lead">GlucoSense unified portal</p>

        <form onSubmit={handleSubmit} className="unified-login-form">
          <label className="unified-field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@clinic.org"
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
            />
          </label>

          <fieldset className="unified-role-fieldset">
            <legend>I am a</legend>
            <label className="unified-radio">
              <input type="radio" name="role" checked={role === 'clinician'} onChange={() => setRole('clinician')} />
              <span>Clinician</span>
            </label>
            <label className="unified-radio">
              <input type="radio" name="role" checked={role === 'patient'} onChange={() => setRole('patient')} />
              <span>Patient</span>
            </label>
          </fieldset>

          <button type="submit" className="unified-btn unified-btn-primary unified-btn-block">
            Continue
          </button>
        </form>

        <p className="unified-login-hint">
          Demo mode: password optional. The Meal Plan panel loads the separate Glocusense web app - run it on{' '}
          <code>127.0.0.1:5173</code> (see <code>VITE_MEAL_PLAN_URL</code>).
        </p>
      </div>
    </div>
  )
}
