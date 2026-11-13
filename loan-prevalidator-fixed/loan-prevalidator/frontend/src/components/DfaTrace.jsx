import { cls } from './ui.jsx'

/** Visualises the DFA path: q0 --L--> q1 --O--> q2 ... */
export default function DfaTrace({ trace = [], finalState = 'q0', accepted = false }) {
  const chip = (s, last) => {
    const dead = s === 'qD'
    const tone = last ? (accepted ? 'bg-emerald-600 text-white' : dead ? 'bg-red-600 text-white' : 'bg-amber-500 text-white') : 'bg-navy-800 text-white'
    return <span className={cls('rounded-md px-2 py-1 font-mono text-xs font-semibold', tone)}>{s}</span>
  }
  return (
    <div>
      <div className="flex flex-wrap items-center gap-1">
        {chip('q0', trace.length === 0)}
        {trace.map((t, i) => (
          <span key={i} className="flex items-center gap-1">
            <span className="flex flex-col items-center text-[10px] leading-none text-slate-500">
              <span className={cls('font-mono text-sm font-bold', t.to === 'qD' ? 'text-red-600' : 'text-navy-700')}>{t.symbol === ' ' ? '␣' : t.symbol}</span>→
            </span>
            {chip(t.to, i === trace.length - 1)}
          </span>
        ))}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Final state <b className="font-mono">{finalState}</b> — {accepted ? 'accepting (q11 ∈ F)' : finalState === 'qD' ? 'dead state (rejected)' : 'non-accepting (rejected)'}
      </p>
    </div>
  )
}
