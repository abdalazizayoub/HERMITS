import { useState, useEffect } from 'react'
import { formatDistanceToNow, isPast, parseISO } from 'date-fns'

interface SLATimerProps {
  dueAt: string | null
  compact?: boolean
}

export default function SLATimer({ dueAt, compact = false }: SLATimerProps) {
  const [, setTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 30_000)
    return () => clearInterval(id)
  }, [])

  if (!dueAt) return <span className="text-slate-500 text-xs">No SLA</span>

  const due = parseISO(dueAt)
  const overdue = isPast(due)
  const label = formatDistanceToNow(due, { addSuffix: true })

  const colorClass = overdue
    ? 'text-red-400'
    : 'text-amber-400'

  if (compact) {
    return <span className={`text-xs ${colorClass}`}>{label}</span>
  }

  return (
    <span className={`text-xs font-mono ${colorClass}`}>
      {overdue ? '⚠ Overdue' : 'SLA'} {label}
    </span>
  )
}
