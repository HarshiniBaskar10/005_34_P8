import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api.js'
import { Card, Stat, usePoll } from './ui.jsx'

const CAT = { Home: '#0b1f3a', Vehicle: '#2563eb', Personal: '#64748b', Education: '#10b981', Invalid: '#ef4444' }
const Empty = () => <p className="py-16 text-center text-sm text-slate-400">No data yet.</p>

export default function AnalyticsDashboard({ tick }) {
  const { data } = usePoll(api.analytics, [tick])
  if (!data) return <p className="text-slate-500">Loading analytics…</p>
  const total = data.categories.reduce((s, c) => s + c.value, 0)
  const resolved = data.resolution[0].value
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <Stat label="Total" value={total} /><Stat label="Resolved" value={resolved} accent="border-emerald-500" />
        <Stat label="Unresolved" value={data.resolution[1].value} accent="border-amber-500" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Zone-wise distribution">
          {!total ? <Empty /> : <ResponsiveContainer width="100%" height={280}><BarChart data={data.zones}><CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" name="Reports" fill="#17386a" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer>}
        </Card>
        <Card title="Category-wise distribution (5 categories)">
          {!total ? <Empty /> : <ResponsiveContainer width="100%" height={280}><BarChart data={data.categories}><CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" name="Reports" radius={[6, 6, 0, 0]}>{data.categories.map((c) => <Cell key={c.name} fill={CAT[c.name]} />)}</Bar></BarChart></ResponsiveContainer>}
        </Card>
        <Card title="Resolved vs unresolved" className="lg:col-span-2">
          {!total ? <Empty /> : <ResponsiveContainer width="100%" height={280}><PieChart><Pie data={data.resolution} dataKey="value" nameKey="name" innerRadius={65} outerRadius={105} label>
            <Cell fill="#10b981" /><Cell fill="#f59e0b" /></Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer>}
        </Card>
      </div>
    </div>
  )
}
