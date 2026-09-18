import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { todayISO } from '../lib/format'
import { ErrorState, FormError, Loading } from '../components/States'

const BLANK = {
  title: '',
  description: '',
  quantity: '',
  unit: 'units',
  delivery_location: '',
  deadline: '',
}

/** Handles both "post a new RFQ" and "edit an existing one". */
export default function RFQForm({ mode = 'create' }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = mode === 'edit'

  const [form, setForm] = useState(BLANK)
  const [loading, setLoading] = useState(isEdit)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [lockedFields, setLockedFields] = useState(false)

  useEffect(() => {
    if (!isEdit) return
    let cancelled = false

    api
      .getRFQ(id)
      .then((rfq) => {
        if (cancelled) return
        setForm({
          title: rfq.title,
          description: rfq.description,
          quantity: String(rfq.quantity),
          unit: rfq.unit,
          delivery_location: rfq.delivery_location,
          deadline: rfq.deadline,
        })
        // Once suppliers have quoted, the API freezes the commercial terms.
        // Disable those inputs so the restriction is visible, not a surprise
        // 409 after the user has retyped the whole form.
        setLockedFields(rfq.quotation_count > 0)
      })
      .catch((err) => !cancelled && setLoadError(err.message))
      .finally(() => !cancelled && setLoading(false))

    return () => {
      cancelled = true
    }
  }, [id, isEdit])

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)

    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      quantity: Number(form.quantity),
      unit: form.unit.trim() || 'units',
      delivery_location: form.delivery_location.trim(),
      deadline: form.deadline,
    }

    try {
      if (isEdit) {
        // Send only what this RFQ still allows changing.
        const patch = lockedFields
          ? { description: payload.description, deadline: payload.deadline }
          : payload
        await api.updateRFQ(id, patch)
        navigate(`/buyer/rfqs/${id}`)
      } else {
        const created = await api.createRFQ(payload)
        navigate(`/buyer/rfqs/${created.id}`)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Loading label="Loading RFQ…" />
  if (loadError) return <ErrorState message={loadError} onRetry={() => window.location.reload()} />

  return (
    <section className="narrow">
      <div className="page-head">
        <div>
          <h1>{isEdit ? 'Edit RFQ' : 'Post an RFQ'}</h1>
          <p className="muted">
            {isEdit
              ? 'Update your requirement.'
              : 'Describe what you need. Suppliers will see it as soon as you post.'}
          </p>
        </div>
      </div>

      {lockedFields && (
        <div className="notice" role="status">
          Suppliers have already quoted on this RFQ, so quantity, location and title are locked.
          You can still clarify the description or extend the deadline.
        </div>
      )}

      <form className="card form" onSubmit={handleSubmit} noValidate>
        <label htmlFor="title">Product or service name</label>
        <input
          id="title"
          value={form.title}
          onChange={update('title')}
          disabled={lockedFields}
          required
          minLength={3}
          maxLength={200}
          placeholder="e.g. 500 galvanised steel brackets"
        />

        <label htmlFor="description">Requirement description</label>
        <textarea
          id="description"
          rows={6}
          value={form.description}
          onChange={update('description')}
          required
          minLength={10}
          maxLength={5000}
          placeholder="Specifications, materials, standards, tolerances, packaging…"
        />

        <div className="form-row">
          <div>
            <label htmlFor="quantity">Quantity</label>
            <input
              id="quantity"
              type="number"
              min={1}
              value={form.quantity}
              onChange={update('quantity')}
              disabled={lockedFields}
              required
            />
          </div>
          <div>
            <label htmlFor="unit">Unit</label>
            <input
              id="unit"
              value={form.unit}
              onChange={update('unit')}
              disabled={lockedFields}
              placeholder="pieces, kg, sets…"
            />
          </div>
        </div>

        <label htmlFor="location">Delivery location</label>
        <input
          id="location"
          value={form.delivery_location}
          onChange={update('delivery_location')}
          disabled={lockedFields}
          required
          placeholder="City, State"
        />

        <label htmlFor="deadline">RFQ deadline</label>
        <input
          id="deadline"
          type="date"
          min={todayISO()}
          value={form.deadline}
          onChange={update('deadline')}
          required
        />
        <small className="hint">Suppliers cannot quote after this date.</small>

        <FormError message={error} />

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Post RFQ'}
          </button>
        </div>
      </form>
    </section>
  )
}
