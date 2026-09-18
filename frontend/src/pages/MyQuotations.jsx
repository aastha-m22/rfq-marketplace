import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { formatDate, formatPrice } from '../lib/format'
import { Badge, Empty, ErrorState, Loading } from '../components/States'

export default function MyQuotations() {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' })

  const load = useCallback(async () => {
    setState({ status: 'loading', data: null, error: '' })
    try {
      const data = await api.myQuotations()
      setState({ status: 'ready', data, error: '' })
    } catch (err) {
      setState({ status: 'error', data: null, error: err.message })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>My Quotations</h1>
          <p className="muted">Everything you have quoted on, newest first.</p>
        </div>
      </div>

      {state.status === 'loading' && <Loading label="Loading your quotations…" />}
      {state.status === 'error' && <ErrorState message={state.error} onRetry={load} />}

      {state.status === 'ready' &&
        (state.data.length === 0 ? (
          <Empty
            title="No quotations yet"
            hint="Find an open requirement and submit your first quote."
            action={
              <Link className="btn btn-primary" to="/browse">
                Browse RFQs
              </Link>
            }
          />
        ) : (
          <div className="quote-list">
            {state.data.map((q) => (
              <article key={q.id} className={`card quote-card ${q.status}`}>
                <div className="quote-head">
                  <Link to={`/rfqs/${q.rfq_id}`} className="quote-rfq-title">
                    {q.rfq.title}
                  </Link>
                  <Badge status={q.status} />
                </div>

                <div className="quote-figures">
                  <div>
                    <span className="label">Your price</span>
                    <span className="value">{formatPrice(q.price)}</span>
                  </div>
                  <div>
                    <span className="label">Delivery</span>
                    <span className="value">{q.delivery_days} days</span>
                  </div>
                  <div>
                    <span className="label">RFQ deadline</span>
                    <span className="value">{formatDate(q.rfq.deadline)}</span>
                  </div>
                  <div>
                    <span className="label">Submitted</span>
                    <span className="value">{formatDate(q.created_at)}</span>
                  </div>
                </div>

                {q.notes && <p className="quote-notes">{q.notes}</p>}
              </article>
            ))}
          </div>
        ))}
    </section>
  )
}
