import type { MonthlyDigestResult } from '../../types/digest'
import { Ticket, Clock, AlertCircle, TrendingUp } from 'lucide-react'

export default function StatsCards({ data }: { data: MonthlyDigestResult }) {
  const cards = [
    {
      label: 'Tickets Resolved',
      value: data.total_tickets,
      icon: Ticket,
      color: 'text-blue-400',
      bg: 'bg-blue-950/30 border-blue-800/50',
    },
    {
      label: 'Avg Resolution',
      value: `${data.avg_resolution_minutes.toFixed(0)} min`,
      icon: Clock,
      color: 'text-emerald-400',
      bg: 'bg-emerald-950/30 border-emerald-800/50',
    },
    {
      label: 'Most Common Root Cause',
      value: data.most_common_root_cause,
      icon: AlertCircle,
      color: 'text-amber-400',
      bg: 'bg-amber-950/30 border-amber-800/50',
      truncate: true,
    },
    {
      label: 'Top Incidents',
      value: data.top_incidents.length,
      icon: TrendingUp,
      color: 'text-purple-400',
      bg: 'bg-purple-950/30 border-purple-800/50',
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map(({ label, value, icon: Icon, color, bg, truncate }) => (
        <div key={label} className={`rounded-xl border p-4 ${bg}`}>
          <div className="flex items-center gap-2 mb-2">
            <Icon size={14} className={color} />
            <span className="text-xs text-slate-400">{label}</span>
          </div>
          <p className={`text-lg font-bold ${color} ${truncate ? 'text-sm font-medium leading-snug' : ''}`}>
            {String(value)}
          </p>
        </div>
      ))}
    </div>
  )
}
