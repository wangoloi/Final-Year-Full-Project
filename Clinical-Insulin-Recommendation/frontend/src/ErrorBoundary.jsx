import React from 'react'

/**
 * Avoid a blank screen when a child throws — shows the error for debugging.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('GlucoSense render error:', error, info?.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            minHeight: '100vh',
            padding: '2rem',
            fontFamily: 'system-ui, sans-serif',
            background: '#fef2f2',
            color: '#991b1b',
          }}
        >
          <h1 style={{ fontSize: '1.1rem', margin: '0 0 0.75rem' }}>Something went wrong</h1>
          <pre
            style={{
              margin: 0,
              padding: '1rem',
              background: '#fff',
              borderRadius: 8,
              overflow: 'auto',
              fontSize: 13,
              border: '1px solid #fecaca',
            }}
          >
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <p style={{ marginTop: '1rem', fontSize: 14, color: '#64748b' }}>
            Refresh the page. If this persists, check the browser console (F12).
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
