import { useEffect, useState } from 'react'

const RESOURCES = [
  { id: 'hypo', title: 'Hypoglycemia protocol', content: 'Recognize and treat low blood glucose (below 70 mg/dL). Administer 15–20 g fast-acting carbohydrate; recheck in 15 minutes. If severe or unable to swallow, use glucagon per protocol. Document event and adjust future insulin/carb ratios with the care team.' },
  { id: 'diet', title: 'Dietary guidance', content: 'Carbohydrate counting and meal planning support glycemic control. Encourage consistent carb intake at meals, fiber-rich choices, and portion awareness. Consider timing of rapid-acting insulin (e.g. 15–20 min before meals) per individual response.' },
  { id: 'exercise', title: 'Exercise recommendations', content: 'Physical activity can lower glucose during and after exercise. Recommend pre-exercise glucose check; consider reducing insulin or consuming carbs before/during prolonged activity. Monitor for delayed hypoglycemia up to 24 hours post-exercise.' },
]

export default function ResourcePanel({ open, onClose, resourceId: initialResourceId }) {
  const [selectedId, setSelectedId] = useState(initialResourceId || null)

  useEffect(() => {
    if (open) setSelectedId(initialResourceId || null)
  }, [open, initialResourceId])

  useEffect(() => {
    if (!open) return
    const handle = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handle)
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', handle); document.body.style.overflow = '' }
  }, [open, onClose])

  if (!open) return null

  const resource = selectedId ? RESOURCES.find((r) => r.id === selectedId) : null

  return (
    <div className="modal-overlay resource-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="resource-panel" onClick={(e) => e.stopPropagation()}>
        <div className="resource-panel-header">
          <h2>{resource ? resource.title : 'Clinical resources'}</h2>
          <button type="button" className="resource-panel-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="resource-panel-body">
          {resource ? (
            <>
              <p>{resource.content}</p>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setSelectedId(null)}>Back to list</button>
            </>
          ) : (
            <ul className="resource-list">
              {RESOURCES.map((r) => (
                <li key={r.id}>
                  <button type="button" className="resource-link" onClick={() => setSelectedId(r.id)}>{r.title}</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
