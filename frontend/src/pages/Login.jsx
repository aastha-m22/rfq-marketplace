import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { FormError } from '../components/States'

const DEMO = [
  { label: 'Demo buyer', email: 'buyer@demo.com' },
  { label: 'Demo supplier', email: 'supplier@demo.com' },
]

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={user.role === 'buyer' ? '/buyer/rfqs' : '/browse'} replace />

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const signedIn = await login(form)
      const fallback = signedIn.role === 'buyer' ? '/buyer/rfqs' : '/browse'
      navigate(location.state?.from || fallback, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  function fillDemo(email) {
    setForm({ email, password: 'password123' })
    setError('')
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Log in</h1>
        <p className="muted">Post requirements, or find work to quote on.</p>

        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={update('email')}
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={form.password}
            onChange={update('password')}
            required
          />

          <FormError message={error} />

          <button className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Logging in…' : 'Log in'}
          </button>
        </form>

        <div className="demo-row">
          <span className="muted">Try it:</span>
          {DEMO.map((d) => (
            <button key={d.email} className="btn btn-ghost btn-sm" onClick={() => fillDemo(d.email)}>
              {d.label}
            </button>
          ))}
        </div>

        <p className="auth-switch">
          No account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  )
}
