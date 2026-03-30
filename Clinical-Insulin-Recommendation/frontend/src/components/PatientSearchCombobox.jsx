/**
 * Searchable patient picker: shows name only; still matches on name, condition, or id when searching.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

function patientLabel(p) {
  return String(p.name || '').trim()
}

export default function PatientSearchCombobox({
  patients = [],
  value,
  onChange,
  disabled = false,
  placeholder = 'Search by name or ID…',
  id = 'patient-search-combobox',
}) {
  const containerRef = useRef(null)
  const listRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [highlight, setHighlight] = useState(0)

  const selected = useMemo(
    () => (patients || []).find((p) => p.id === value || String(p.id) === String(value)),
    [patients, value],
  )

  useEffect(() => {
    if (selected) {
      setQuery(patientLabel(selected))
    } else if (value == null || value === '') {
      setQuery('')
    }
  }, [value, selected?.id])

  const normalized = (query || '').trim().toLowerCase()
  const filtered = useMemo(() => {
    const list = patients || []
    if (!normalized) return list
    return list.filter((p) => {
      const blob = `${p.name || ''} ${p.condition || ''} ${p.id}`.toLowerCase()
      return blob.includes(normalized)
    })
  }, [patients, normalized])

  useEffect(() => {
    setHighlight(0)
  }, [normalized, open])

  useEffect(() => {
    const onDoc = (e) => {
      if (!containerRef.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const pick = useCallback(
    (p) => {
      onChange?.(p.id)
      setQuery(patientLabel(p))
      setOpen(false)
    },
    [onChange],
  )

  const handleInputChange = (e) => {
    const v = e.target.value
    setQuery(v)
    setOpen(true)
    if (value != null && selected) {
      if (v !== patientLabel(selected)) onChange?.(null)
    }
  }

  const handleFocus = () => {
    setOpen(true)
  }

  const handleBlur = () => {
    window.setTimeout(() => {
      setOpen(false)
      if (value == null || value === '') {
        setQuery('')
      } else if (selected) {
        setQuery(patientLabel(selected))
      }
    }, 180)
  }

  const onKeyDown = (e) => {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter')) {
      setOpen(true)
      return
    }
    if (!open) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlight((h) => Math.min(h + 1, Math.max(0, filtered.length - 1)))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((h) => Math.max(0, h - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filtered[highlight]) pick(filtered[highlight])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  useEffect(() => {
    if (!open || !listRef.current) return
    const el = listRef.current.querySelector(`[data-idx="${highlight}"]`)
    el?.scrollIntoView?.({ block: 'nearest' })
  }, [highlight, open])

  const listboxId = `${id}-listbox`

  return (
    <div className="patient-search-combobox" ref={containerRef}>
      <input
        id={id}
        type="text"
        className="form-input"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-activedescendant={open && filtered[highlight] ? `${id}-opt-${highlight}` : undefined}
        autoComplete="off"
        placeholder={placeholder}
        value={query}
        onChange={handleInputChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      {open && patients.length === 0 && (
        <div className="patient-search-dropdown patient-search-empty" role="status">
          No patients registered.
        </div>
      )}
      {open && patients.length > 0 && filtered.length > 0 && (
        <ul
          ref={listRef}
          id={listboxId}
          className="patient-search-dropdown"
          role="listbox"
        >
          {filtered.map((p, i) => (
            <li
              key={p.id}
              id={`${id}-opt-${i}`}
              data-idx={i}
              role="option"
              aria-selected={highlight === i}
              className={`patient-search-option ${highlight === i ? 'patient-search-option--active' : ''}`}
              onMouseDown={(e) => {
                e.preventDefault()
                pick(p)
              }}
              onMouseEnter={() => setHighlight(i)}
            >
              <span className="patient-search-name">{p.name}</span>
            </li>
          ))}
        </ul>
      )}
      {open && patients.length > 0 && normalized && filtered.length === 0 && (
        <div className="patient-search-dropdown patient-search-empty" role="status">
          No patients match &quot;{query.trim()}&quot;.
        </div>
      )}
    </div>
  )
}
