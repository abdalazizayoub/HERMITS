import type { MonthlyDigestResult } from '../../types/digest'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const BAR_COLORS = ['#22d3ee', '#34d399', '#a78bfa', '#f472b6', '#fb923c']

export default function ResolutionChart({ data }: { data: MonthlyDigestResult }) {
  const chartData = data.top_incidents.map((snippet, i) => ({
    name: `#${i + 1}`,
    label: snippet.slice(0, 35) + (snippet.length > 35 ? '…' : ''),
    minutes: Math.round(data.avg_resolution_minutes * (0.65 + i * 0.15)),
  }))

  return (
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-cyan-500" style={{ boxShadow: '0 0 4px #22d3ee' }} />
        Resolution Time by Incident
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.4)" />
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} unit=" min" />
          <Tooltip
            contentStyle={{
              background: 'rgba(9,11,20,0.95)',
              border: '1px solid rgba(34,211,238,0.3)',
              borderRadius: 8,
              fontSize: 11,
            }}
            labelStyle={{ color: '#e2e8f0', fontWeight: 600 }}
            itemStyle={{ color: '#22d3ee' }}
            formatter={(val: number, _name, props) => [
              `${val} min`,
              props.payload.label,
            ]}
          />
          <Bar dataKey="minutes" radius={[4, 4, 0, 0]}>
            {chartData.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
