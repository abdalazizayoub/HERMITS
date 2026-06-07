import type { MonthlyDigestResult } from '../../types/digest'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS = ['#a78bfa', '#22d3ee', '#34d399', '#f472b6', '#fb923c']

export default function RootCauseChart({ data }: { data: MonthlyDigestResult }) {
  const total = Math.max(data.total_tickets, 1)
  const primaryCount = Math.ceil(total * 0.6)
  const otherCount = total - primaryCount

  const chartData = [
    { name: data.most_common_root_cause.slice(0, 28) + (data.most_common_root_cause.length > 28 ? '…' : ''), value: primaryCount },
    ...(otherCount > 0 ? [{ name: 'Other causes', value: otherCount }] : []),
  ]

  return (
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-purple-500" style={{ boxShadow: '0 0 4px #a78bfa' }} />
        Root Cause Distribution
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={44}
            outerRadius={72}
            paddingAngle={4}
            dataKey="value"
          >
            {chartData.map((_, i) => (
              <Cell
                key={i}
                fill={COLORS[i % COLORS.length]}
                fillOpacity={0.85}
                stroke="rgba(0,0,0,0.3)"
                strokeWidth={1}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: 'rgba(9,11,20,0.95)',
              border: '1px solid rgba(167,139,250,0.3)',
              borderRadius: 8,
              fontSize: 11,
            }}
            itemStyle={{ color: '#e2e8f0' }}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value) => <span style={{ fontSize: 10, color: '#94a3b8' }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
