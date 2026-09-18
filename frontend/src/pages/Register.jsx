import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { FormError } from '../components/States'

export default function Register() {
  const { user, register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'buyer',
    company_name: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={user.role === 'buyer' ? '/buyer/rfqs' : '/browse'} replace />

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    // Cheap client-side check that mirrors the API's rule, so the user gets
    // feedback without a round trip. The API still validates independently.
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setSubmitting(true)
    try {
      const created = await register({
        ...form,
        company_name: form.company_name.trim() || null,
      })
      navigate(created.role === 'buyer' ? '/buyer/rfqs' : '/browse', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Create an account</h1>
        <p className="muted">Choose how you will use the marketplace.</p>

        <form onSubmit={handleSubmit} noValidate>
          <fieldset className="role-picker">
            <legend>I am a</legend>
            {[
              { value: 'buyer', title: 'Buyer', hint: 'Post requirements and receive quotes' },
              { value: 'supplier', title: 'Supplier', hint: 'Find requirements and submit quotes' },
            ].map((option) => (
              <label
                key={option.value}
                className={`role-option ${form.role === option.value ? 'selected' : ''}`}
              >
                <input
                  type="radio"
                  name="role"
                  value={option.value}
                  checked={form.role === option.value}
                  onChange={update('role')}
                />
                <strong>{option.title}</strong>
                <small>{option.hint}</small>
              </label>
            ))}
          </fieldset>

          <label htmlFor="name">Full name</label>
          <input id="name" value={form.name} onChange={update('name')} required minLength={2} />

          <label htmlFor="company">Company name</label>
          <input
            id="company"
            value={form.company_name}
            onChange={update('company_name')}
            placeholder="Optional"
          />

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
            autoComplete="new-password"
            value={form.password}
            onChange={update('password')}
            required
          />
          <small className="hint">At least 8 characters.</small>

          <FormError message={error} />

          <button className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  )
}
