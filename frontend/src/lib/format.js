/** Shared formatting helpers, so currency and dates look the same everywhere. */

const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
})

export function formatPrice(value) {
  const n = Number(value)
  return Number.isFinite(n) ? currency.format(n) : String(value)
}

export function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** "in 5 days" / "today" / "3 days ago" for RFQ deadlines. */
export function deadlineLabel(dateString) {
  const deadline = new Date(`${dateString}T00:00:00`)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const days = Math.round((deadline - today) / 86_400_000)
  if (days === 0) return 'closes today'
  if (days === 1) return 'closes tomorrow'
  if (days > 1) return `closes in ${days} days`
  return `closed ${Math.abs(days)} day${days === -1 ? '' : 's'} ago`
}

export function todayISO() {
  return new Date().toISOString().slice(0, 10)
}
