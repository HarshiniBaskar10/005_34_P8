async function j(url, opts = {}) {
  const r = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(d.error || `Request failed (${r.status})`)
  return d
}
const body = (b) => JSON.stringify(b)
export const api = {
  validate: (b) => j('/api/validate', { method: 'POST', body: body(b) }),
  submit: (b) => j('/api/reports', { method: 'POST', body: body(b) }),
  report: (id) => j(`/api/reports/${encodeURIComponent(id)}`),
  reports: (qs = '') => j(`/api/reports${qs}`),
  advance: (id) => j(`/api/reports/${id}/advance`, { method: 'POST' }),
  stats: () => j('/api/stats'),
  handlers: () => j('/api/handlers'),
  setHandler: (id, b) => j(`/api/handlers/${id}`, { method: 'PATCH', body: body(b) }),
  routing: () => j('/api/routing'),
  analytics: () => j('/api/analytics'),
  seed: () => j('/api/seed', { method: 'POST' }),
  reset: () => j('/api/reset', { method: 'POST' }),
}
