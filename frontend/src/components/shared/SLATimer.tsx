import { useState, useEffect } from 'react'
import { formatDistanceToNow, isPast, parseISO } from 'date-fns'
import { Clock } from 'lucide-react'

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

  if (!dueAt) return null

  const due = parseISO(dueAt)
  const overdue = isPast(due)
  const label = formatDistanceToNow(due, { addSuffix: true })

  if (compact) {
    return (
      <span className={`text-xs font-mono ${overdue ? 'text-red-400' : 'text-amber-400'}`}>
        {overdue ? '⚠' : '⏱'} {label}
      </span>
    )
  }

  return (
    <span className={`text-xs font-mono flex items-center gap-1 ${overdue ? 'text-red-400' : 'text-amber-400'}`}>
      <Clock size={10} />
      {overdue ? 'OVERDUE' : 'SLA'} {label}
    </span>
  )
}
