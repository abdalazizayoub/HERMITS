import type { MonthlyDigestResult } from '../../types/digest'
import { TicketCheck, Clock, AlertCircle, TrendingUp } from 'lucide-react'

export default function StatsCards({ data }: { data: MonthlyDigestResult }) {
  const cards = [
    {
      label: 'Tickets Resolved',
      value: String(data.total_tickets),
      icon: TicketCheck,
      color: 'text-cyan-400',
      border: 'rgba(34,211,238,0.25)',
      bg: 'rgba(34,211,238,0.06)',
      glow: 'drop-shadow(0 0 6px #22d3ee)',
    },
    {
      label: 'Avg Resolution',
      value: `${data.avg_resolution_minutes.toFixed(0)} min`,
      icon: Clock,
      color: 'text-emerald-400',
      border: 'rgba(52,211,153,0.25)',
      bg: 'rgba(52,211,153,0.06)',
      glow: 'drop-shadow(0 0 6px #34d399)',
    },
    {
      label: 'Top Root Cause',
      value: data.most_common_root_cause,
      icon: AlertCircle,
      color: 'text-amber-400',
      border: 'rgba(251,191,36,0.25)',
      bg: 'rgba(251,191,36,0.06)',
      glow: 'drop-shadow(0 0 6px #fbbf24)',
      small: true,
    },
    {
      label: 'Incidents Tracked',
      value: String(data.top_incidents.length),
      icon: TrendingUp,
      color: 'text-purple-400',
      border: 'rgba(167,139,250,0.25)',
      bg: 'rgba(167,139,250,0.06)',
      glow: 'drop-shadow(0 0 6px #a78bfa)',
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map(({ label, value, icon: Icon, color, border, bg, glow, small }) => (
        <div
          key={label}
          className="rounded-xl border p-4"
          style={{ borderColor: border, background: bg }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Icon size={14} className={color} style={{ filter: glow }} />
            <span className="text-xs text-slate-500 leading-tight">{label}</span>
          </div>
          <p className={`font-bold ${color} ${small ? 'text-xs leading-snug' : 'text-2xl'}`}>
            {value}
          </p>
        </div>
      ))}
    </div>
  )
}
