import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { deadlineLabel, formatDate } from '../lib/format'
import { Badge, Empty, ErrorState, Loading } from '../components/States'

export default function MyRFQs() {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' })

  const load = useCallback(async () => {
    setState({ status: 'loading', data: null, error: '' })
    try {
      const data = await api.myRFQs()
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
          <h1>My RFQs</h1>
          <p className="muted">Requirements you have posted, and the quotes they attracted.</p>
        </div>
        <Link className="btn btn-primary" to="/buyer/rfqs/new">
          Post an RFQ
        </Link>
      </div>

      {state.status === 'loading' && <Loading label="Loading your RFQs…" />}
      {state.status === 'error' && <ErrorState message={state.error} onRetry={load} />}

      {state.status === 'ready' &&
        (state.data.items.length === 0 ? (
          <Empty
            title="No RFQs yet"
            hint="Post your first requirement and suppliers can start quoting."
            action={
              <Link className="btn btn-primary" to="/buyer/rfqs/new">
                Post an RFQ
              </Link>
            }
          />
        ) : (
          <div className="grid">
            {state.data.items.map((rfq) => (
              <Link key={rfq.id} to={`/buyer/rfqs/${rfq.id}`} className="card rfq-card">
                <div className="rfq-card-head">
                  <h3>{rfq.title}</h3>
                  <Badge status={rfq.status} />
                </div>
                <p className="rfq-desc">{rfq.description}</p>
                <dl className="rfq-meta">
                  <div>
                    <dt>Quantity</dt>
                    <dd>
                      {rfq.quantity.toLocaleString('en-IN')} {rfq.unit}
                    </dd>
                  </div>
                  <div>
                    <dt>Deliver to</dt>
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
                <footer className="rfq-card-foot">
                  {rfq.quotation_count === 0
                    ? 'No quotations yet'
                    : `${rfq.quotation_count} quotation${rfq.quotation_count === 1 ? '' : 's'}`}
                </footer>
              </Link>
            ))}
          </div>
        ))}
    </section>
  )
}
