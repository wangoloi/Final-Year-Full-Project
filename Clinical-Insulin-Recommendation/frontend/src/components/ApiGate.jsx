import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

const API_RETRY_MS = 2000
const API_RETRY_ATTEMPTS = 30

async function waitForApi() {
  for (let i = 0; i < API_RETRY_ATTEMPTS; i++) {
    try {
      const r = await apiFetch('/api/health/live')
      if (r.ok) return { ok: true }
    } catch (_) {
      /* retry */
    }
    await new Promise((resolve) => setTimeout(resolve, API_RETRY_MS))
  }
  return { ok: false }
}

/**
 * Wraps clinician workspace only — blocks until GlucoSense API is reachable.
 */
export default function ApiGate({ children }) {
  const [state, setState] = useState('loading')

  useEffect(() => {
    waitForApi().then((result) => setState(result.ok ? 'ready' : 'failed'))
  }, [])

  if (state === 'loading') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'system-ui', color: '#666' }}>
        Connecting to GlucoSense…
      </div>
    )
  }

  if (state === 'failed') {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          fontFamily: 'system-ui',
          color: '#333',
          padding: '1.5rem',
          maxWidth: 520,
          margin: '0 auto',
          textAlign: 'center',
        }}
      >
        <h1 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>Cannot reach the GlucoSense API</h1>
        <p style={{ color: '#555', lineHeight: 1.5, marginBottom: '1rem' }}>
          Start the GlucoSense backend on port <strong>8000</strong>, then refresh.
        </p>
        <code style={{ display: 'block', background: '#f4f4f5', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.85rem', textAlign: 'left', width: '100%' }}>
          python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
        </code>
        <button
          type="button"
          onClick={() => window.location.reload()}
          style={{ marginTop: '1.25rem', padding: '0.5rem 1.25rem', cursor: 'pointer', borderRadius: 8, border: '1px solid #ccc', background: '#fff' }}
        >
          Retry
        </button>
      </div>
    )
  }

  return children
}
