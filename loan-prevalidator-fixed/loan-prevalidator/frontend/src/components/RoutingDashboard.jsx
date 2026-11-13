import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Card, Table, cls, eventTone, fmtMoney, fmtTime, urgencyTone, usePoll } from './ui.jsx'

export default function RoutingDashboard({ tick }) {
  const { data } = usePoll(api.routing, [tick])
  const [filter, setFilter] = useState('ALL')
  const [cat, setCat] = useState('Home')
  if (!data) return <p className="text-slate-500">Loading routing table…</p>
  const log = data.log.filter((l) => filter === 'ALL' || l.event === filter)
  return (
    <div className="space-y-6">
      <Card title="Routing / dispatch table" right={<span className="text-xs text-slate-500">Key = (category, amount band, zone) · HIGH band ≥ {fmtMoney(data.band_limit)}</span>}>
        <Table head={['Branch', 'Category', 'Band', 'Role', 'Handler', 'Zones served', 'Load', 'Status']}>
          {data.handlers.map((h) => {
            const pct = h.max_capacity ? Math.min(100, (h.current_load / h.max_capacity) * 100) : 100
            return (
              <tr key={h.id}>
                <td className="px-3 py-2 font-medium">{h.branch}</td><td className="px-3 py-2">{h.category}</td>
                <td className="px-3 py-2">{h.band}</td><td className="px-3 py-2"><Badge tone={h.is_backup ? 'amber' : 'blue'}>{h.is_backup ? 'Backup' : 'Primary'}</Badge></td>
                <td className="px-3 py-2">{h.name}</td><td className="px-3 py-2">{h.zones}</td>
                <td className="px-3 py-2 w-44"><div className="h-2 rounded-full bg-slate-200"><div className={cls('h-2 rounded-full', h.current_load > h.max_capacity ? 'bg-red-500' : pct >= 100 ? 'bg-amber-500' : 'bg-emerald-500')} style={{ width: `${pct}%` }} /></div>
                  <span className="text-xs text-slate-500">{h.current_load}/{h.max_capacity}</span></td>
                <td className="px-3 py-2"><Badge tone={h.available ? 'emerald' : 'red'}>{h.available ? 'Available' : 'Offline'}</Badge></td>
              </tr>
            )
          })}
        </Table>
      </Card>
      <Card title="Explicit routing table (category, band, zone → desk, primary, backup)"
        right={<select className="rounded-lg border border-slate-300 px-2 py-1 text-sm" value={cat} onChange={(e) => setCat(e.target.value)}>{['Home', 'Vehicle', 'Personal', 'Education'].map((x) => <option key={x}>{x}</option>)}</select>}>
        <Table head={['Category', 'Band', 'Zone', 'Branch', 'Team', 'Primary handler', 'Backup handler']}>
          {data.table.filter((t) => t.category === cat).map((t) => (
            <tr key={`${t.category}${t.band}${t.zone}`}><td className="px-3 py-2">{t.category}</td><td className="px-3 py-2">{t.band}</td><td className="px-3 py-2">{t.zone}</td>
              <td className="px-3 py-2">{t.branch}</td><td className="px-3 py-2">{t.team}</td><td className="px-3 py-2">{t.primary_name}</td><td className="px-3 py-2">{t.backup_name}</td></tr>
          ))}
        </Table>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={`Waiting queue (${data.waiting.length})`} right={<span className="text-xs text-slate-500">ordered by priority, then time</span>}>
          <Table head={['#', 'Report', 'Category', 'Priority', 'Queued at']} empty={data.waiting.length ? '' : 'No reports waiting.'}>
            {data.waiting.map((r, i) => (
              <tr key={r.report_id}><td className="px-3 py-2">{i + 1}</td><td className="px-3 py-2 font-mono text-xs">{r.report_id}</td><td className="px-3 py-2">{r.category}</td>
                <td className="px-3 py-2"><Badge tone={urgencyTone(r.urgency)}>{r.urgency}</Badge></td><td className="px-3 py-2 text-xs">{fmtTime(r.created_at)}</td></tr>
            ))}
          </Table>
        </Card>
        <Card title={`Central correction / fallback queue (${data.correction.length})`}>
          <Table head={['Report', 'Queue', 'Reason']} empty={data.correction.length ? '' : 'Nothing in correction.'}>
            {data.correction.slice(0, 30).map((r) => (
              <tr key={r.report_id}><td className="px-3 py-2 font-mono text-xs">{r.report_id}</td>
                <td className="px-3 py-2"><Badge tone={r.queue === 'CENTRAL_FALLBACK' ? 'amber' : 'red'}>{r.queue === 'CENTRAL_FALLBACK' ? 'Fallback' : 'Correction'}</Badge></td>
                <td className="px-3 py-2 text-xs"><b>{r.reason_code}</b> {r.reason_text}</td></tr>
            ))}
          </Table>
        </Card>
      </div>
      <Card title="Dispatch, escalation & priority-override log"
        right={<select className="rounded-lg border border-slate-300 px-2 py-1 text-sm" value={filter} onChange={(e) => setFilter(e.target.value)}>
          {['ALL', 'ROUTED', 'ESCALATION', 'PRIORITY_OVERRIDE', 'WAITING', 'FALLBACK', 'REJECTED', 'STATUS', 'AVAILABILITY', 'CAPACITY'].map((x) => <option key={x}>{x}</option>)}</select>}>
        <Table head={['Time', 'Event', 'Report', 'Decision']} empty={log.length ? '' : 'No events.'}>
          {log.map((l) => (
            <tr key={l.id}><td className="px-3 py-2 text-xs whitespace-nowrap text-slate-500">{fmtTime(l.ts)}</td><td className="px-3 py-2"><Badge tone={eventTone(l.event)}>{l.event}</Badge></td>
              <td className="px-3 py-2 font-mono text-xs">{l.report_id || '—'}</td><td className="px-3 py-2 text-xs text-slate-600">{l.detail}</td></tr>
          ))}
        </Table>
      </Card>
    </div>
  )
}
