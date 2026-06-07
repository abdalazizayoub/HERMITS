import type { FixStep, SafetyResult } from '../../types/agent'
import Badge from '../shared/Badge'
import { CheckCircle, Circle, ShieldAlert, AlertTriangle } from 'lucide-react'

interface FixStepListProps {
  steps: FixStep[]
  safetyResults: SafetyResult[]
  currentIndex: number
  executedCount: number
}

export default function FixStepList({ steps, safetyResults, currentIndex, executedCount }: FixStepListProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Fix Steps</p>
      {steps.map((step, i) => {
        const safety = safetyResults[i]
        const isDone = i < executedCount
        const isCurrent = i === currentIndex
        const isBlocked = safety && !safety.is_safe

        return (
          <div
            key={i}
            className={`rounded-lg border p-3 transition-all ${
              isDone
                ? 'border-emerald-800/40 bg-emerald-950/10 opacity-60'
                : isCurrent
                ? 'border-blue-600 bg-blue-950/30 shadow shadow-blue-900/20'
                : isBlocked
                ? 'border-red-800/50 bg-red-950/10 opacity-70'
                : 'border-slate-700 bg-slate-900/50 opacity-50'
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircle size={14} className="text-emerald-400" />
                ) : isBlocked ? (
                  <ShieldAlert size={14} className="text-red-400" />
                ) : (
                  <Circle size={14} className={isCurrent ? 'text-blue-400' : 'text-slate-600'} />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-slate-500">Step {i + 1}</span>
                  <Badge variant={step.risk_level as 'low' | 'medium' | 'high'}>
                    {step.risk_level}
                  </Badge>
                  {isBlocked && <Badge variant="error">BLOCKED</Badge>}
                </div>

                <code className="block text-xs font-mono bg-slate-800 text-emerald-300 px-2 py-1.5 rounded break-all">
                  {step.command}
                </code>

                <p className="text-xs text-slate-400 mt-1">{step.rationale}</p>

                {isBlocked && safety?.reason && (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <ShieldAlert size={10} />
                    {safety.reason}
                  </p>
                )}

                {safety?.warnings && safety.warnings.length > 0 && (
                  <div className="mt-1 space-y-0.5">
                    {safety.warnings.map((w, wi) => (
                      <p key={wi} className="text-xs text-amber-400 flex items-center gap-1">
                        <AlertTriangle size={10} />
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
