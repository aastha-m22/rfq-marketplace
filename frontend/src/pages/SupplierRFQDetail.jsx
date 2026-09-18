import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { deadlineLabel, formatDate, formatPrice } from '../lib/format'
import { Badge, ErrorState, FormError, Loading } from '../components/States'

export default function SupplierRFQDetail() {
  const { id } = useParams()

  const [rfq, setRfq] = useState(null)
  const [myQuote, setMyQuote] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  const [form, setForm] = useState({ price: '', delivery_days: '', notes: '' })
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [saved, setSaved] = useState(false)

  const load = useCallback(async () => {
    setStatus('loading')
    try {
      // There is no "my quote for this RFQ" endpoint by design - a supplier's
      // own quotes are already available in one list, so we filter locally
      // rather than adding an endpoint that returns a single row.
      const [rfqData, mine] = await Promise.all([api.getRFQ(id), api.myQuotations()])
      const existing = mine.find((q) => String(q.rfq_id) === String(id)) || null

      setRfq(rfqData)
      setMyQuote(existing)
      if (existing) {
        setForm({
          price: String(existing.price),
          delivery_days: String(existing.delivery_days),
          notes: existing.notes || '',
        })
      }
      setStatus('ready')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  function update(field) {
    return (e) => {
      setForm((f) => ({ ...f, [field]: e.target.value }))
      setSaved(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError('')
    setSubmitting(true)
    try {
      await api.submitQuotation(id, {
        price: Number(form.price).toFixed(2),
        delivery_days: Number(form.delivery_days),
        notes: form.notes.trim() || null,
      })
      setSaved(true)
      await load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (status === 'loading') return <Loading label="Loading RFQ…" />
  if (status === 'error') return <ErrorState message={error} onRetry={load} />

  const closedReason =
    rfq.status !== 'open'
      ? `This RFQ is ${rfq.status} and is no longer accepting quotations.`
      : rfq.is_expired
        ? 'The deadline for this RFQ has passed.'
        : null

  const quoteLocked = myQuote && myQuote.status !== 'pending'

  return (
    <section>
      <Link to="/browse" className="back-link">
        ← Browse RFQs
      </Link>

      <div className="page-head">
        <div>
          <h1>{rfq.title}</h1>
          <p className="muted">
            {rfq.buyer.company_name || rfq.buyer.name} · posted {formatDate(rfq.created_at)}
          </p>
        </div>
        <Badge status={rfq.status} />
      </div>

      <div className="card">
        <p className="rfq-full-desc">{rfq.description}</p>
        <dl className="rfq-meta wide">
          <div>
            <dt>Quantity</dt>
            <dd>
              {rfq.quantity.toLocaleString('en-IN')} {rfq.unit}
            </dd>
          </div>
          <div>
            <dt>Delivery location</dt>
            <dd>{rfq.delivery_location}</dd>
          </div>
          <div>
            <dt>Deadline</dt>
            <dd>
              {formatDate(rfq.deadline)}
              <span className={`deadline ${rfq.is_expired ? 'expired' : ''}`}>
                {deadlineLabel(rfq.deadline)}
              </span>
            </dd>
          </div>
        </dl>
      </div>

      <h2 className="section-title">{myQuote ? 'Your quotation' : 'Submit a quotation'}</h2>

      {myQuote && (
        <div className={`card quote-card ${myQuote.status}`}>
          <div className="quote-head">
            <strong>Submitted {formatDate(myQuote.created_at)}</strong>
            <Badge status={myQuote.status} />
          </div>
          <div className="quote-figures">
            <div>
              <span className="label">Your price</span>
              <span className="value">{formatPrice(myQuote.price)}</span>
            </div>
            <div>
              <span className="label">Delivery</span>
              <span className="value">{myQuote.delivery_days} days</span>
            </div>
          </div>
          {myQuote.status === 'accepted' && (
            <p className="notice success">The buyer accepted your quotation.</p>
          )}
          {myQuote.status === 'rejected' && (
            <p className="notice">This RFQ was awarded to another supplier.</p>
          )}
        </div>
      )}

      {closedReason && !quoteLocked ? (
        <div className="notice" role="status">
          {closedReason}
        </div>
      ) : quoteLocked ? null : (
        <form className="card form" onSubmit={handleSubmit} noValidate>
          {myQuote && (
            <p className="hint">
              You can revise your quotation until the buyer accepts one or the deadline passes.
            </p>
          )}

          <div className="form-row">
            <div>
              <label htmlFor="price">Quoted price (INR)</label>
              <input
                id="price"
                type="number"
                min="0.01"
                step="0.01"
                value={form.price}
                onChange={update('price')}
                required
                placeholder="0.00"
              />
            </div>
            <div>
              <label htmlFor="days">Estimated delivery (days)</label>
              <input
                id="days"
                type="number"
                min="1"
                value={form.delivery_days}
                onChange={update('delivery_days')}
                required
                placeholder="e.g. 14"
              />
            </div>
          </div>

          <label htmlFor="notes">Message / notes</label>
          <textarea
            id="notes"
            rows={4}
            value={form.notes}
            onChange={update('notes')}
            maxLength={2000}
            placeholder="Payment terms, freight, sample availability, substitutions…"
          />

          <FormError message={formError} />
          {saved && !formError && <p className="form-success">Quotation saved.</p>}

          <button className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Submitting…' : myQuote ? 'Update quotation' : 'Submit quotation'}
          </button>
        </form>
      )}
    </section>
  )
}
