import { useState } from 'react'
import { api } from './api.js'
import SubmitPage from './components/SubmitPage.jsx'
import UserDashboard from './components/UserDashboard.jsx'
import HandlerDashboard from './components/HandlerDashboard.jsx'
import RoutingDashboard from './components/RoutingDashboard.jsx'
import AnalyticsDashboard from './components/AnalyticsDashboard.jsx'
import { cls } from './components/ui.jsx'

const TABS = [['submit', 'Report Submission'], ['user', 'User Dashboard'], ['handler', 'Handler Dashboard'], ['routing', 'Routing Management'], ['analytics', 'Analytics']]

export default function App() {
  const [tab, setTab] = useState('submit')
  const [tick, setTick] = useState(0)
  const [toast, setToast] = useState(null)
  const bump = () => setTick((t) => t + 1)
  const run = async (fn, ok) => {
    try { const d = await fn(); setToast({ ok: true, text: ok(d) }); bump() } catch (e) { setToast({ ok: false, text: e.message }) }
    setTimeout(() => setToast(null), 4000)
  }
  return (
    <div className="min-h-screen">
      <header className="bg-navy-900 text-white shadow">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div><h1 className="text-lg font-semibold tracking-tight">P8 · Loan Application Pre-Validator</h1>
            <p className="text-xs text-slate-300">BCS503 Automata (DFA ≡ Regex) · BCS502 Networks (Routing & Dispatch)</p></div>
          <div className="flex gap-2">
            <button onClick={() => run(api.seed, (d) => `Seeded ${d.created} applications`)} className="rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-400">Seed Realistic Test Applications</button>
            <button onClick={() => window.confirm('Delete all reports and logs?') && run(api.reset, () => 'Database cleared')} className="rounded-lg bg-white/10 px-3 py-2 text-sm font-medium hover:bg-white/20">Reset</button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4">
          {TABS.map(([k, label]) => (
            <button key={k} onClick={() => setTab(k)} className={cls('whitespace-nowrap rounded-t-lg px-4 py-2 text-sm font-medium transition', tab === k ? 'bg-slate-100 text-navy-900' : 'text-slate-300 hover:bg-white/10')}>{label}</button>
          ))}
        </nav>
      </header>
      {toast && <div className={cls('fixed right-4 top-4 z-50 rounded-lg px-4 py-3 text-sm text-white shadow-lg', toast.ok ? 'bg-emerald-600' : 'bg-red-600')}>{toast.text}</div>}
      <main className="mx-auto max-w-7xl px-4 py-6">
        {tab === 'submit' && <SubmitPage onChange={bump} />}
        {tab === 'user' && <UserDashboard tick={tick} />}
        {tab === 'handler' && <HandlerDashboard tick={tick} onChange={bump} />}
        {tab === 'routing' && <RoutingDashboard tick={tick} />}
        {tab === 'analytics' && <AnalyticsDashboard tick={tick} />}
      </main>
    </div>
  )
}
