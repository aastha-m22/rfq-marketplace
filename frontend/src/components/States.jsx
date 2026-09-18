/**
 * The three states every async view needs.
 *
 * Having them as shared components rather than ad-hoc JSX means no screen
 * quietly forgets one and renders a blank page while loading.
 */

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  )
}

export function Empty({ title, hint, action }) {
  return (
    <div className="state">
      <h3>{title}</h3>
      {hint && <p className="muted">{hint}</p>}
      {action}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state state-error" role="alert">
      <h3>Something went wrong</h3>
      <p className="muted">{message}</p>
      {onRetry && (
        <button className="btn btn-secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

/** Inline form-level error, e.g. a rejected login or a 409 from the API. */
export function FormError({ message }) {
  if (!message) return null
  return (
    <p className="form-error" role="alert">
      {message}
    </p>
  )
}

export function Badge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>
}
