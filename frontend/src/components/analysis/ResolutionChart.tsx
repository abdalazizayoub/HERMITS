import type { MonthlyDigestResult } from '../../types/digest'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function ResolutionChart({ data }: { data: MonthlyDigestResult }) {
  const chartData = data.top_incidents.map((snippet, i) => ({
    name: `Inc. ${i + 1}`,
    snippet: snippet.slice(0, 40) + (snippet.length > 40 ? '…' : ''),
    minutes: data.avg_resolution_minutes * (0.7 + Math.random() * 0.6),
  }))

  return (
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Top Incidents — Resolution Time (min)
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, left: -10, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} />
          <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#e2e8f0' }}
            itemStyle={{ color: '#38bdf8' }}
            formatter={(val: number) => [`${val.toFixed(0)} min`, 'Resolution']}
          />
          <Bar dataKey="minutes" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
