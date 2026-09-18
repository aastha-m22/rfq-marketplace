import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { deadlineLabel, formatDate } from '../lib/format'
import { Empty, ErrorState, Loading } from '../components/States'

const PAGE_SIZE = 9

export default function BrowseRFQs() {
  // `filters` is what the user is typing; `applied` is what has been searched.
  // Keeping them separate means the list does not refetch on every keystroke.
  const [filters, setFilters] = useState({ q: '', location: '', sort: 'newest' })
  const [applied, setApplied] = useState({ q: '', location: '', sort: 'newest' })
  const [page, setPage] = useState(1)

  const [state, setState] = useState({ status: 'loading', data: null, error: '' })

  const load = useCallback(async () => {
    setState((s) => ({ ...s, status: 'loading' }))
    try {
      const params = { page, page_size: PAGE_SIZE, sort: applied.sort }
      if (applied.q.trim()) params.q = applied.q.trim()
      if (applied.location.trim()) params.location = applied.location.trim()

      const data = await api.browseRFQs(params)
      setState({ status: 'ready', data, error: '' })
    } catch (err) {
      setState({ status: 'error', data: null, error: err.message })
    }
  }, [applied, page])

  useEffect(() => {
    load()
  }, [load])

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
    setApplied(filters)
  }

  function handleReset() {
    const cleared = { q: '', location: '', sort: 'newest' }
    setFilters(cleared)
    setApplied(cleared)
    setPage(1)
  }

  const hasFilters = applied.q || applied.location
  const totalPages = state.data ? Math.max(1, Math.ceil(state.data.total / PAGE_SIZE)) : 1

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Browse RFQs</h1>
          <p className="muted">Open requirements you can still quote on.</p>
        </div>
      </div>

      <form className="card filters" onSubmit={handleSearch}>
        <div className="filter-fields">
          <div>
            <label htmlFor="q">Search</label>
            <input
              id="q"
              value={filters.q}
              onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
              placeholder="Product, material, specification…"
            />
          </div>
          <div>
            <label htmlFor="location">Delivery location</label>
            <input
              id="location"
              value={filters.location}
              onChange={(e) => setFilters((f) => ({ ...f, location: e.target.value }))}
              placeholder="City or state"
            />
          </div>
          <div>
            <label htmlFor="sort">Sort by</label>
            <select
              id="sort"
              value={filters.sort}
              onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value }))}
            >
              <option value="newest">Newest first</option>
              <option value="deadline">Closing soonest</option>
            </select>
          </div>
        </div>
        <div className="filter-actions">
          <button className="btn btn-primary">Search</button>
          {hasFilters && (
            <button type="button" className="btn btn-ghost" onClick={handleReset}>
              Clear
            </button>
          )}
        </div>
      </form>

      {state.status === 'loading' && <Loading label="Finding RFQs…" />}
      {state.status === 'error' && <ErrorState message={state.error} onRetry={load} />}

      {state.status === 'ready' &&
        (state.data.items.length === 0 ? (
          <Empty
            title={hasFilters ? 'No RFQs match your search' : 'No open RFQs right now'}
            hint={
              hasFilters
                ? 'Try a broader search term or clear the filters.'
                : 'Check back shortly — buyers post new requirements regularly.'
            }
            action={
              hasFilters ? (
                <button className="btn btn-secondary" onClick={handleReset}>
                  Clear filters
                </button>
              ) : null
            }
          />
        ) : (
          <>
            <p className="result-count">
              {state.data.total} open RFQ{state.data.total === 1 ? '' : 's'}
            </p>

            <div className="grid">
              {state.data.items.map((rfq) => (
                <Link key={rfq.id} to={`/rfqs/${rfq.id}`} className="card rfq-card">
                  <div className="rfq-card-head">
                    <h3>{rfq.title}</h3>
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
                        <span className="deadline">{deadlineLabel(rfq.deadline)}</span>
                      </dd>
                    </div>
                  </dl>
                  <footer className="rfq-card-foot">
                    {rfq.buyer.company_name || rfq.buyer.name}
                  </footer>
                </Link>
              ))}
            </div>

            {totalPages > 1 && (
              <nav className="pagination">
                <button
                  className="btn btn-secondary"
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </button>
                <span>
                  Page {page} of {totalPages}
                </span>
                <button
                  className="btn btn-secondary"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </nav>
            )}
          </>
        ))}
    </section>
  )
}
