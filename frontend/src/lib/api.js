/**
 * Thin fetch wrapper.
 *
 * Every network call in the app goes through `request`, so the token header,
 * JSON encoding and error shape are defined once. Components never touch
 * fetch directly and never have to remember to attach auth.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'rfq_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** Error carrying the HTTP status, so callers can branch on 401 vs 409. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const token = getToken()
  if (auth && token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    // fetch only rejects on network-level failure, never on a 4xx/5xx.
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0)
  }

  if (response.status === 204) return null

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or revoked: drop it so the router sends us to login.
      setToken(null)
    }
    throw new ApiError(payload?.detail || `Request failed (${response.status})`, response.status)
  }

  return payload
}

export const api = {
  register: (data) => request('/api/auth/register', { method: 'POST', body: data, auth: false }),
  login: (data) => request('/api/auth/login', { method: 'POST', body: data, auth: false }),
  me: () => request('/api/auth/me'),

  browseRFQs: (params) => request(`/api/rfqs?${new URLSearchParams(params)}`),
  myRFQs: () => request('/api/rfqs/mine'),
  getRFQ: (id) => request(`/api/rfqs/${id}`),
  createRFQ: (data) => request('/api/rfqs', { method: 'POST', body: data }),
  updateRFQ: (id, data) => request(`/api/rfqs/${id}`, { method: 'PATCH', body: data }),
  deleteRFQ: (id) => request(`/api/rfqs/${id}`, { method: 'DELETE' }),

  rfqQuotations: (id) => request(`/api/rfqs/${id}/quotations`),
  submitQuotation: (id, data) =>
    request(`/api/rfqs/${id}/quotations`, { method: 'POST', body: data }),
  myQuotations: () => request('/api/quotations/mine'),
  acceptQuotation: (id) => request(`/api/quotations/${id}/accept`, { method: 'POST' }),
}
