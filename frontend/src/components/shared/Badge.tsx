interface BadgeProps {
  variant: 'critical' | 'high' | 'open' | 'done' | 'low' | 'medium' | 'error'
  children: React.ReactNode
  className?: string
}

const VARIANTS = {
  critical: 'bg-red-500/15 text-red-400 border border-red-500/50 shadow-sm',
  high: 'bg-orange-500/15 text-orange-400 border border-orange-500/50 shadow-sm',
  open: 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/50',
  done: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/50',
  low: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40',
  medium: 'bg-amber-500/15 text-amber-400 border border-amber-500/50',
  error: 'bg-red-500/15 text-red-400 border border-red-500/40',
}

export default function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-semibold tracking-wide ${VARIANTS[variant]} ${className}`}>
      {children}
    </span>
  )
}
