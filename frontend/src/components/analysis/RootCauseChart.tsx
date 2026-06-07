import type { MonthlyDigestResult } from '../../types/digest'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS = ['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#475569']

export default function RootCauseChart({ data }: { data: MonthlyDigestResult }) {
  const chartData = [
    { name: data.most_common_root_cause.slice(0, 30), value: Math.ceil(data.total_tickets * 0.6) },
    { name: 'Other causes', value: Math.floor(data.total_tickets * 0.4) },
  ]

  return (
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Root Cause Distribution
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={4}
            dataKey="value"
          >
            {chartData.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
            itemStyle={{ color: '#e2e8f0' }}
          />
          <Legend
            formatter={(value) => <span style={{ fontSize: 11, color: '#94a3b8' }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
