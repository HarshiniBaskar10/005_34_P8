import { useEffect, useState } from 'react'

export const cls = (...a) => a.filter(Boolean).join(' ')
const TONE = {
  emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', amber: 'bg-amber-50 text-amber-800 ring-amber-600/30',
  red: 'bg-red-50 text-red-700 ring-red-600/20', blue: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  slate: 'bg-slate-100 text-slate-700 ring-slate-500/20',
}
export const statusTone = (s) => ({ Pending: 'amber', Assigned: 'blue', 'In Progress': 'blue', Resolved: 'emerald' }[s] || 'slate')
export const urgencyTone = (u) => ({ Critical: 'red', High: 'amber', Normal: 'slate' }[u] || 'slate')
export const eventTone = (e) => ({ ROUTED: 'emerald', ESCALATION: 'amber', PRIORITY_OVERRIDE: 'red', WAITING: 'amber', FALLBACK: 'red', REJECTED: 'red', STATUS: 'blue' }[e] || 'slate')
export const fmtMoney = (v) => (v === '' || v == null || isNaN(v) ? '—' : '₹' + Number(v).toLocaleString('en-IN'))
export const fmtTime = (t) => (t ? new Date(t).toLocaleString() : '—')

export function Badge({ tone = 'slate', children }) {
  return <span className={cls('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap', TONE[tone])}>{children}</span>
}
export function Card({ title, right, children, className }) {
  return (
    <section className={cls('rounded-xl bg-white shadow-sm ring-1 ring-slate-200', className)}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-2 border-b border-slate-100 px-5 py-3">
          <h2 className="text-sm font-semibold tracking-wide text-navy-900 uppercase">{title}</h2>{right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}
export function Stat({ label, value, accent = 'border-navy-700' }) {
  return (
    <div className={cls('rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 border-l-4', accent)}>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-navy-900">{value ?? '—'}</div>
    </div>
  )
}
export const Table = ({ head, children, empty }) => (
  <div className="overflow-x-auto">
    <table className="min-w-full text-left text-sm">
      <thead><tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">{head.map((h) => <th key={h} className="px-3 py-2 font-medium whitespace-nowrap">{h}</th>)}</tr></thead>
      <tbody className="divide-y divide-slate-100">{children}</tbody>
    </table>
    {empty && <p className="px-3 py-6 text-center text-sm text-slate-400">{empty}</p>}
  </div>
)
export const inputCls = 'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-700/20'
export const btn = 'rounded-lg px-3 py-2 text-sm font-medium shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50'
export const btnPrimary = cls(btn, 'bg-navy-800 text-white hover:bg-navy-700')
export const btnGhost = cls(btn, 'bg-white text-navy-800 ring-1 ring-slate-300 hover:bg-slate-50')

/** Polls an async fn every `ms`; re-runs when deps (e.g. a global refresh tick) change. */
export function usePoll(fn, deps = [], ms = 4000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    let alive = true
    const run = () => fn().then((d) => { if (alive) { setData(d); setError(null) } }).catch((e) => alive && setError(e.message))
    run()
    const t = setInterval(run, ms)
    return () => { alive = false; clearInterval(t) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return { data, error }
}
