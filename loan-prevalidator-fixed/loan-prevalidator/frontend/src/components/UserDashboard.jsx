import { useEffect, useState } from 'react'
import { api } from '../api.js'
import DfaTrace from './DfaTrace.jsx'
import { Badge, Card, Stat, Table, eventTone, fmtMoney, fmtTime, inputCls, statusTone, urgencyTone, usePoll } from './ui.jsx'

export default function UserDashboard({ tick }) {
  const { data: stats } = usePoll(api.stats, [tick])
  const { data: list } = usePoll(() => api.reports('?sort=recent'), [tick])
  const [q, setQ] = useState('')
  const [found, setFound] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!q.trim()) { setFound(null); setErr(null); return }
    const t = setTimeout(() => api.report(q.trim()).then((d) => { setFound(d); setErr(null) }).catch((e) => { setFound(null); setErr(e.message) }), 250)
    return () => clearTimeout(t)
  }, [q, tick])

  const r = found?.report
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label="Total reports" value={stats?.total} />
        <Stat label="Pending" value={stats?.pending} accent="border-amber-500" />
        <Stat label="Assigned / In progress" value={stats ? stats.assigned + stats.in_progress : null} accent="border-blue-500" />
        <Stat label="Resolved" value={stats?.resolved} accent="border-emerald-500" />
        <Stat label="In correction queue" value={stats?.correction} accent="border-red-500" />
      </div>
      <Card title="Track a report">
        <input className={inputCls} placeholder="Search by Report ID, e.g. RPT-1A2B3C4D" value={q} onChange={(e) => setQ(e.target.value)} />
        {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
        {r && (
          <div className="mt-4 grid gap-6 lg:grid-cols-2">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Report ID</dt><dd className="font-mono font-semibold">{r.report_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Application</dt><dd className="font-mono">{r.application_code || '—'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Status</dt><dd><Badge tone={statusTone(r.status)}>{r.status}</Badge></dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Category</dt><dd><Badge tone={r.category === 'Invalid' ? 'red' : 'emerald'}>{r.category}</Badge></dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Assigned handler</dt><dd>{r.handler_name ? `${r.handler_name} · ${r.branch}` : 'Not assigned'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Assigned at</dt><dd>{fmtTime(r.assigned_at)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Queue</dt><dd>{r.queue || '—'}</dd></div>
              {r.reason_code && <p className="rounded-lg bg-red-50 p-3 text-red-700">{r.reason_code}: {r.reason_text}</p>}
              <p className="text-xs text-slate-500">{r.route_decision}</p>
              <div className="pt-2"><div className="mb-2 text-xs font-semibold uppercase text-slate-500">DFA audit trace</div>
                <DfaTrace trace={r.dfa_trace} finalState={r.dfa_trace.at(-1)?.to || 'q0'} accepted={!!r.dfa_accept} /></div>
            </dl>
            <div>
              <div className="mb-2 text-xs font-semibold uppercase text-slate-500">Routing audit trail</div>
              <ol className="space-y-2 border-l-2 border-slate-200 pl-4">
                {found.log.map((l, i) => (
                  <li key={i} className="text-sm"><Badge tone={eventTone(l.event)}>{l.event}</Badge>
                    <span className="ml-2 text-xs text-slate-400">{fmtTime(l.ts)}</span><p className="text-slate-600">{l.detail}</p></li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </Card>
      <Card title="Recent reports">
        <Table head={['Report ID', 'Code', 'Category', 'Urgency', 'Amount', 'Status', 'Handler']} empty={list?.reports.length ? '' : 'No reports yet — submit one or use “Seed Realistic Test Applications”.'}>
          {list?.reports.map((x) => (
            <tr key={x.report_id} className="cursor-pointer hover:bg-slate-50" onClick={() => setQ(x.report_id)}>
              <td className="px-3 py-2 font-mono text-xs">{x.report_id}</td><td className="px-3 py-2 font-mono text-xs">{x.application_code || '—'}</td>
              <td className="px-3 py-2"><Badge tone={x.category === 'Invalid' ? 'red' : 'emerald'}>{x.category}</Badge></td>
              <td className="px-3 py-2"><Badge tone={urgencyTone(x.urgency)}>{x.urgency}</Badge></td>
              <td className="px-3 py-2">{fmtMoney(x.amount)}</td>
              <td className="px-3 py-2"><Badge tone={statusTone(x.status)}>{x.status}</Badge></td>
              <td className="px-3 py-2">   {x.handler_name || ({ CENTRAL_CORRECTION: 'Correction queue', CENTRAL_FALLBACK: 'Fallback queue', WAITING: 'Waiting queue' }[x.queue]) || '—'}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  )
}
