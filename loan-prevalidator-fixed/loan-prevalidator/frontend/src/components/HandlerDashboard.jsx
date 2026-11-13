import { useState } from 'react'
import { api } from '../api.js'
import { Badge, Card, Table, btnGhost, btnPrimary, cls, fmtMoney, fmtTime, inputCls, statusTone, urgencyTone, usePoll } from './ui.jsx'

export default function HandlerDashboard({ tick, onChange }) {
  const [hid, setHid] = useState(null)
  const [msg, setMsg] = useState(null)
  const { data: hs } = usePoll(api.handlers, [tick])
  const handlers = hs?.handlers || []
  const current = handlers.find((h) => h.id === hid) || handlers[0]
  const { data: rs } = usePoll(() => (current ? api.reports(`?handler_id=${current.id}`) : Promise.resolve({ reports: [] })), [tick, current?.id])
  const act = async (fn) => { try { setMsg(null); await fn(); onChange() } catch (e) { setMsg(e.message) } }
  const [cap, setCap] = useState('')

  return (
    <div className="grid gap-6 lg:grid-cols-4">
      <Card title="Handlers" className="lg:col-span-1">
        <ul className="space-y-2">
          {handlers.map((h) => (
            <li key={h.id}>
              <button onClick={() => { setHid(h.id); setCap('') }} className={cls('w-full rounded-lg px-3 py-2 text-left text-sm ring-1 transition', h.id === current?.id ? 'bg-navy-800 text-white ring-navy-800' : 'bg-white ring-slate-200 hover:bg-slate-50')}>
                <div className="flex items-center justify-between"><span className="font-medium">{h.name}</span>
                  <span className={cls('h-2 w-2 rounded-full', h.available ? 'bg-emerald-400' : 'bg-red-400')} /></div>
                <div className={cls('text-xs', h.id === current?.id ? 'text-slate-300' : 'text-slate-500')}>{h.branch} · {h.is_backup ? 'Backup' : h.band} · {h.current_load}/{h.max_capacity}</div>
              </button>
            </li>
          ))}
        </ul>
      </Card>
      <div className="space-y-6 lg:col-span-3">
        {current && (
          <Card title={`${current.name} — ${current.branch}`} right={<Badge tone={current.available ? 'emerald' : 'red'}>{current.available ? 'Available' : 'Offline'}</Badge>}>
            <div className="flex flex-wrap items-end gap-3">
              <button className={btnPrimary} onClick={() => act(() => api.setHandler(current.id, { available: !current.available }))}>
                {current.available ? 'Go offline' : 'Go available'}
              </button>
              <label className="text-sm font-medium">Max capacity
                <input type="number" min="0" max="50" className={cls(inputCls, 'mt-1 w-28')} placeholder={current.max_capacity} value={cap} onChange={(e) => setCap(e.target.value)} />
              </label>
              <button className={btnGhost} disabled={cap === ''} onClick={() => act(async () => { await api.setHandler(current.id, { max_capacity: parseInt(cap, 10) }); setCap('') })}>Update capacity</button>
              <p className="text-sm text-slate-500">Load <b>{current.current_load}</b> / {current.max_capacity} · {current.zones} zone(s) · {current.is_backup ? 'backup' : `${current.band} band`}</p>
            </div>
            {msg && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{msg}</p>}
          </Card>
        )}
        <Card title="Assigned reports">
          <Table head={['Report ID', 'Category', 'Zone', 'Priority', 'Amount', 'Submitted', 'Assigned', 'Status', 'Action']} empty={rs?.reports.length ? '' : 'No reports assigned to this handler.'}>
            {rs?.reports.map((r) => (
              <tr key={r.report_id}>
                <td className="px-3 py-2 font-mono text-xs">{r.report_id}</td><td className="px-3 py-2">{r.category}</td><td className="px-3 py-2">{r.zone}</td>
                <td className="px-3 py-2"><Badge tone={urgencyTone(r.urgency)}>{r.urgency}</Badge></td><td className="px-3 py-2">{fmtMoney(r.amount)}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{fmtTime(r.created_at)}</td><td className="px-3 py-2 text-xs text-slate-500">{fmtTime(r.assigned_at)}</td>
                <td className="px-3 py-2"><Badge tone={statusTone(r.status)}>{r.status}</Badge></td>
                <td className="px-3 py-2">{r.status === 'Assigned' && <button className={btnGhost} onClick={() => act(() => api.advance(r.report_id))}>Start →</button>}
                  {r.status === 'In Progress' && <button className={btnPrimary} onClick={() => act(() => api.advance(r.report_id))}>Resolve ✓</button>}</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>
    </div>
  )
}
