import { useEffect } from 'react'

export default function SuccessToast({ message, show, onDismiss, duration }) {
  const d = duration ?? 4000
  useEffect(() => {
    if (!show || !onDismiss) return
    const t = setTimeout(onDismiss, d)
    return () => clearTimeout(t)
  }, [show, onDismiss, d])

  if (!show) return null

  return (
    <div className="toast toast-success" role="status" aria-live="polite">
      <span className="toast-icon">✓</span>
      <span>{message}</span>
    </div>
  )
}
