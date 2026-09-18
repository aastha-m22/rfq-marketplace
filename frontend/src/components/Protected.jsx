import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { Loading } from './States'

/**
 * Route guard.
 *
 * `role` restricts a route to buyers or suppliers. This is a UX guard only -
 * it stops someone landing on a screen that would just 403. The real
 * authorization lives in the API's require_buyer / require_supplier
 * dependencies, which a hand-crafted request cannot skip.
 */
export default function Protected({ role, children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <Loading label="Checking your session…" />

  if (!user) {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === 'buyer' ? '/buyer/rfqs' : '/browse'} replace />
  }

  return children
}
