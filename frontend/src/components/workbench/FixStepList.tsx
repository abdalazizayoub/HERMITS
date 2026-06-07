import type { FixStep, SafetyResult } from '../../types/agent'
import Badge from '../shared/Badge'
import { CheckCircle2, Circle, ShieldAlert, AlertTriangle, Zap } from 'lucide-react'

interface FixStepListProps {
  steps: FixStep[]
  safetyResults: SafetyResult[]
  currentIndex: number
  executedCount: number
}

const RISK_COLORS = {
  low: 'text-emerald-400',
  medium: 'text-amber-400',
  high: 'text-red-400',
}

export default function FixStepList({ steps, safetyResults, currentIndex, executedCount }: FixStepListProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Zap size={11} className="text-cyan-600" />
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Fix Steps ({executedCount}/{steps.length} done)
        </p>
      </div>
      {steps.map((step, i) => {
        const safety = safetyResults[i]
        const isDone = i < executedCount
        const isCurrent = i === currentIndex && !isDone
        const isBlocked = safety && !safety.is_safe
        const isUpcoming = i > currentIndex && !isDone

        return (
          <div
            key={i}
            className={`rounded-lg border p-2.5 transition-all ${
              isDone
                ? 'border-emerald-500/20 bg-emerald-950/10 opacity-50'
                : isCurrent
                ? 'border-cyan-500/50 bg-cyan-950/20 neon-border-cyan'
                : isBlocked
                ? 'border-red-500/30 bg-red-950/10 opacity-75'
                : isUpcoming
                ? 'border-slate-800/50 bg-slate-900/30 opacity-40'
                : 'border-slate-700 bg-slate-900/50'
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircle2 size={13} className="text-emerald-400" />
                ) : isBlocked ? (
                  <ShieldAlert size={13} className="text-red-400" />
                ) : (
                  <Circle size={13} className={isCurrent ? 'text-cyan-400' : 'text-slate-700'} />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-slate-600 font-mono">#{i + 1}</span>
                  <Badge variant={step.risk_level as 'low' | 'medium' | 'high'}>
                    {step.risk_level}
                  </Badge>
                  {isBlocked && <Badge variant="error">BLOCKED</Badge>}
                </div>

                <code className={`block text-xs font-mono bg-slate-950 px-2 py-1.5 rounded border border-slate-800/60 break-all ${RISK_COLORS[step.risk_level] ?? 'text-emerald-400'}`}>
                  {step.command}
                </code>

                <p className="text-xs text-slate-500 mt-1 leading-relaxed">{step.rationale}</p>

                {isBlocked && safety?.reason && (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <ShieldAlert size={9} />
                    {safety.reason}
                  </p>
                )}

                {safety?.warnings && safety.warnings.length > 0 && (
                  <div className="mt-1 space-y-0.5">
                    {safety.warnings.map((w, wi) => (
                      <p key={wi} className="text-xs text-amber-500 flex items-center gap-1">
                        <AlertTriangle size={9} />
                        {w}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
