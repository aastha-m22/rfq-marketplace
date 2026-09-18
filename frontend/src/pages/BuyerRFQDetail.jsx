import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { deadlineLabel, formatDate, formatPrice } from '../lib/format'
import { Badge, Empty, ErrorState, FormError, Loading } from '../components/States'

export default function BuyerRFQDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [rfq, setRfq] = useState(null)
  const [quotations, setQuotations] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setStatus('loading')
    setError('')
    try {
      // Both requests are independent, so fire them together rather than
      // waiting for the RFQ before asking for its quotations.
      const [rfqData, quoteData] = await Promise.all([api.getRFQ(id), api.rfqQuotations(id)])
      setRfq(rfqData)
      setQuotations(quoteData)
      setStatus('ready')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  async function handleAccept(quotationId) {
    setActionError('')
    setBusyId(quotationId)
    try {
      await api.acceptQuotation(quotationId)
      await load()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  async function handleClose() {
    setActionError('')
    try {
      await api.updateRFQ(id, { status: 'closed' })
      await load()
    } catch (err) {
      setActionError(err.message)
    }
  }

  async function handleDelete() {
    setActionError('')
    try {
      await api.deleteRFQ(id)
      navigate('/buyer/rfqs', { replace: true })
    } catch (err) {
      setActionError(err.message)
    }
  }

  if (status === 'loading') return <Loading label="Loading RFQ…" />
  if (status === 'error') return <ErrorState message={error} onRetry={load} />

  const canEdit = rfq.status === 'open'
  const canDelete = rfq.status === 'open' && rfq.quotation_count === 0
  const isAwarded = rfq.status === 'awarded'

  return (
    <section>
      <Link to="/buyer/rfqs" className="back-link">
        ← My RFQs
      </Link>

      <div className="page-head">
        <div>
          <h1>{rfq.title}</h1>
          <p className="muted">
            Posted {formatDate(rfq.created_at)} · <Badge status={rfq.status} />
          </p>
        </div>
        <div className="action-row">
          {canEdit && (
            <Link className="btn btn-secondary" to={`/buyer/rfqs/${id}/edit`}>
              Edit
            </Link>
          )}
          {canEdit && quotations.length > 0 && (
            <button className="btn btn-secondary" onClick={handleClose}>
              Close RFQ
            </button>
          )}
          {canDelete && (
            <button className="btn btn-danger" onClick={handleDelete}>
              Delete
            </button>
          )}
        </div>
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

      <h2 className="section-title">
        Quotations received
        {quotations.length > 0 && <span className="count">{quotations.length}</span>}
      </h2>

      <FormError message={actionError} />

      {quotations.length === 0 ? (
        <Empty
          title="No quotations yet"
          hint={
            rfq.is_expired
              ? 'This RFQ expired before any supplier quoted.'
              : 'Suppliers can see this RFQ. Quotes will appear here as they come in.'
          }
        />
      ) : (
        <div className="quote-list">
          {quotations.map((q) => (
            <article key={q.id} className={`card quote-card ${q.status}`}>
              <div className="quote-head">
                <div>
                  <strong>{q.supplier.company_name || q.supplier.name}</strong>
                  <span className="muted"> · {q.supplier.name}</span>
                </div>
                <Badge status={q.status} />
              </div>

              <div className="quote-figures">
                <div>
                  <span className="label">Quoted price</span>
                  <span className="value">{formatPrice(q.price)}</span>
                </div>
                <div>
                  <span className="label">Delivery</span>
                  <span className="value">{q.delivery_days} days</span>
                </div>
                <div>
                  <span className="label">Submitted</span>
                  <span className="value">{formatDate(q.created_at)}</span>
                </div>
              </div>

              {q.notes && <p className="quote-notes">{q.notes}</p>}

              {!isAwarded && (
                <button
                  className="btn btn-primary"
                  onClick={() => handleAccept(q.id)}
                  disabled={busyId !== null}
                >
                  {busyId === q.id ? 'Accepting…' : 'Accept this quotation'}
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
