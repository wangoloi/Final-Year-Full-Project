/**
 * Database backup and restore section.
 * Safe storage with timestamped backups.
 */
import { useState, useEffect } from 'react'
import { FiSave, FiRotateCcw } from 'react-icons/fi'
import { createBackup, fetchBackups, restoreBackup } from '../../services/patientsApi'

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function BackupSection() {
  const [backups, setBackups] = useState([])
  const [creating, setCreating] = useState(false)
  const [restoring, setRestoring] = useState(null)
  const [message, setMessage] = useState(null)

  const load = () => {
    fetchBackups().then(({ backups: list }) => setBackups(list))
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async () => {
    setCreating(true)
    setMessage(null)
    try {
      const { ok, error } = await createBackup()
      if (ok) {
        setMessage('Backup created successfully.')
        load()
      } else {
        setMessage(error || 'Backup failed.')
      }
    } catch (e) {
      setMessage(e.message || 'Backup failed.')
    } finally {
      setCreating(false)
    }
  }

  const handleRestore = async (filename) => {
    if (!window.confirm('Restore from this backup? This will replace the current database.')) return
    setRestoring(filename)
    setMessage(null)
    try {
      const { ok, error } = await restoreBackup(filename)
      if (ok) {
        setMessage('Restore complete. Refreshing...')
        window.location.reload()
      } else {
        setMessage(error || 'Restore failed.')
      }
    } catch (e) {
      setMessage(e.message || 'Restore failed.')
    } finally {
      setRestoring(null)
    }
  }

  return (
    <section className="card backup-section">
      <h2 className="card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <FiSave size={20} style={{ color: 'var(--primary)' }} /> Data backup & restore
      </h2>
      <p className="card-description">
        Create timestamped backups to avoid data loss. Backups are stored in outputs/backups/.
      </p>
      {message && (
        <div className={`alert ${message.includes('success') ? 'alert-success' : 'alert-warning'}`} role="alert">
          {message}
        </div>
      )}
      <div className="form-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleCreate}
          disabled={creating}
        >
          <FiSave size={16} /> {creating ? 'Creating...' : 'Create backup'}
        </button>
      </div>
      <h3 className="records-section-header" style={{ marginTop: 'var(--spacing-md)' }}>Available backups</h3>
      {backups.length === 0 ? (
        <p className="card-description" style={{ margin: 0 }}>No backups yet.</p>
      ) : (
        <ul className="backup-list">
          {backups.map((b) => (
            <li key={b.filename} className="backup-item">
              <div>
                <span className="backup-item-filename">{b.filename}</span>
                <span className="backup-item-meta">
                  {' '}• {formatSize(b.size_bytes)} • {new Date(b.created_at).toLocaleString()}
                </span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleRestore(b.filename)}
                disabled={restoring === b.filename}
              >
                <FiRotateCcw size={14} /> {restoring === b.filename ? 'Restoring...' : 'Restore'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
