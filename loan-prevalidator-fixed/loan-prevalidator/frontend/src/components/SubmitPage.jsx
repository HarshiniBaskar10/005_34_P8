import { useEffect, useState } from 'react'
import { api } from '../api.js'
import DfaTrace from './DfaTrace.jsx'
import { Badge, Card, btnPrimary, btnGhost, cls, fmtMoney, inputCls, statusTone, urgencyTone } from './ui.jsx'

const ZONES = ['North', 'South', 'East', 'West', 'Central']
const EMPTY = { reporter_name: '', reporter_contact: '', application_code: '', income: '', amount: '', zone: 'South', description: '', urgency: 'Normal' }

export default function SubmitPage({ onChange }) {
  const [f, setF] = useState(EMPTY)
  const [live, setLive] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  useEffect(() => {   // debounced live validation (DFA + regex + money regex)
    const t = setTimeout(() => api.validate(f).then(setLive).catch(() => setLive(null)), 200)
    return () => clearTimeout(t)
  }, [f.application_code, f.income, f.amount, f.description, f.reporter_contact])

  const code = live?.code
  const detected = f.application_code ? (live?.classification?.category || '…') : '—'
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError(null)
    try { const { report } = await api.submit(f); setResult(report); onChange(); if (report.is_valid) setF(EMPTY) }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  const fieldMsg = (r) => r && (r.ok ? <p className="mt-1 text-xs text-emerald-600">✓ Valid format</p> : <p className="mt-1 text-xs text-red-600">{r.reason_code}: {r.reason}</p>)
  const border = (r) => (r ? (r.ok ? 'border-emerald-500' : 'border-red-400') : '')

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <Card title="Loan Application Report" className="lg:col-span-3">
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium">Reporter name
            <input className={inputCls} value={f.reporter_name} onChange={set('reporter_name')} placeholder="Loan officer name" />
          </label>
          <label className="text-sm font-medium">Zone
            <input className={inputCls} list="zones" value={f.zone} onChange={set('zone')} placeholder="South" />
            <datalist id="zones">{ZONES.map((z) => <option key={z} value={z} />)}</datalist>
          </label>
          <label className="text-sm font-medium sm:col-span-2">Reporter contact (10-digit mobile)
            <input className={cls(inputCls, f.reporter_contact && border(live?.contact))} value={f.reporter_contact} onChange={set('reporter_contact')} placeholder="9876543210" inputMode="numeric" />
            {f.reporter_contact && fieldMsg(live?.contact)}
          </label>
          <label className="text-sm font-medium sm:col-span-2">Application code <span className="font-mono text-xs text-slate-400">LOAN[H|V|P|E][6 digits] · H=Home V=Vehicle P=Personal E=Education</span>
            <input className={cls(inputCls, 'font-mono tracking-wider', f.application_code && border(code))} value={f.application_code}
              onChange={set('application_code')} placeholder="LOANH104920" spellCheck={false} />
            {f.application_code && (code?.ok ? <p className="mt-1 text-xs text-emerald-600">✓ Accepted by DFA and regex</p> : code && <p className="mt-1 text-xs text-red-600">{code.reason_code}: {code.reason}</p>)}
          </label>
          <label className="text-sm font-medium">Annual income (₹)
            <input className={cls(inputCls, border(live?.income))} value={f.income} onChange={set('income')} placeholder="1800000" inputMode="decimal" />
            {fieldMsg(live?.income)}
            {live?.income && <p className="mt-1 text-[11px] text-slate-400">DFA {live.income.dfa_accept ? 'accept' : 'reject'} · Regex {live.income.regex_accept ? 'accept' : 'reject'}</p>}
          </label>
          <label className="text-sm font-medium">Loan amount (₹)
            <input className={cls(inputCls, border(live?.amount))} value={f.amount} onChange={set('amount')} placeholder="6500000" inputMode="decimal" />
            {fieldMsg(live?.amount)}
            {live?.amount && <p className="mt-1 text-[11px] text-slate-400">DFA {live.amount.dfa_accept ? 'accept' : 'reject'} · Regex {live.amount.regex_accept ? 'accept' : 'reject'}</p>}
          </label>
          <label className="text-sm font-medium sm:col-span-2">Description
            <textarea className={inputCls} rows={3} value={f.description} onChange={set('description')} placeholder="Purpose of the loan…" />
          </label>
          <label className="text-sm font-medium">Urgency
            <select className={inputCls} value={f.urgency} onChange={set('urgency')}>
              <option>Normal</option><option>High</option><option>Critical</option>
            </select>
          </label>
          <div className="flex items-end gap-2 sm:justify-end">
            <button type="button" className={btnGhost} onClick={() => { setF(EMPTY); setResult(null); setError(null) }}>Clear</button>
            <button disabled={busy} className={btnPrimary}>{busy ? 'Submitting…' : 'Validate & Submit'}</button>
          </div>
          {error && <p className="sm:col-span-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </form>
      </Card>

      <div className="space-y-6 lg:col-span-2">
        <Card title="Live DFA vs Regex">
          {!f.application_code || !code ? <p className="text-sm text-slate-400">Start typing an application code to watch the automaton run.</p> : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg bg-slate-50 p-3"><div className="text-xs text-slate-500">DFA</div><Badge tone={code.dfa_accept ? 'emerald' : 'red'}>{code.dfa_accept ? 'ACCEPT' : 'REJECT'}</Badge></div>
                <div className="rounded-lg bg-slate-50 p-3"><div className="text-xs text-slate-500">Regex</div><Badge tone={code.regex_accept ? 'emerald' : 'red'}>{code.regex_accept ? 'ACCEPT' : 'REJECT'}</Badge></div>
              </div>
              <p className="text-xs">Agreement: <Badge tone={code.agree ? 'emerald' : 'red'}>{code.agree ? 'DFA ≡ Regex' : 'MISMATCH'}</Badge></p>
              <DfaTrace trace={code.trace} finalState={code.final_state} accepted={code.dfa_accept} />
              <div className="flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
                <span>Detected category</span><Badge tone={detected === 'Invalid' ? 'red' : detected === '—' ? 'slate' : 'emerald'}>{detected}</Badge>
              </div>
              {live?.classification?.conflict_note && <p className="rounded-lg bg-amber-50 p-2 text-xs text-amber-800">{live.classification.conflict_note}</p>}
              <div className="flex items-center justify-between text-sm"><span>Priority</span><Badge tone={urgencyTone(f.urgency)}>{f.urgency}</Badge></div>
            </div>
          )}
        </Card>

        {result && (
          <Card title="Submission Result" right={<Badge tone={statusTone(result.status)}>{result.status}</Badge>}>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Report ID</dt><dd className="font-mono font-semibold text-navy-900">{result.report_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Category</dt><dd><Badge tone={result.category === 'Invalid' ? 'red' : 'emerald'}>{result.category}</Badge></dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Amount</dt><dd>{fmtMoney(result.amount)}</dd></div>
              {result.branch && <div className="flex justify-between"><dt className="text-slate-500">Branch</dt><dd>{result.branch}</dd></div>}
              {result.reason_code && <p className="rounded-lg bg-red-50 p-3 text-red-700">{result.reason_code}: {result.reason_text}</p>}
              {result.conflict_note && <p className="rounded-lg bg-amber-50 p-3 text-amber-800">{result.conflict_note}</p>}
              <p className="text-xs text-slate-500">{result.route_decision}</p>
            </dl>
          </Card>
        )}
      </div>
    </div>
  )
}
