interface BadgeProps {
  variant: 'critical' | 'high' | 'open' | 'done' | 'low' | 'medium' | 'error'
  children: React.ReactNode
  className?: string
}

const VARIANTS = {
  critical: 'bg-red-900/60 text-red-300 border border-red-700',
  high: 'bg-amber-900/60 text-amber-300 border border-amber-700',
  open: 'bg-blue-900/60 text-blue-300 border border-blue-700',
  done: 'bg-emerald-900/60 text-emerald-300 border border-emerald-700',
  low: 'bg-emerald-900/60 text-emerald-300 border border-emerald-700',
  medium: 'bg-amber-900/60 text-amber-300 border border-amber-700',
  error: 'bg-red-900/60 text-red-300 border border-red-700',
}

export default function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${VARIANTS[variant]} ${className}`}>
      {children}
    </span>
  )
}
