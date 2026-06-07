import type { Hypothesis } from '../../types/agent'
import { Brain, ChevronRight, Shield } from 'lucide-react'

export default function HypothesisCard({ hypothesis }: { hypothesis: Hypothesis }) {
  return (
    <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-3 space-y-2.5 neon-border-purple">
      <div className="flex items-start gap-2">
        <Brain size={14} className="text-purple-400 mt-0.5 shrink-0" style={{ filter: 'drop-shadow(0 0 4px #a78bfa)' }} />
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-100 leading-tight">{hypothesis.hypothesis_title}</p>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">{hypothesis.root_cause_explanation}</p>
        </div>
      </div>

      {hypothesis.evidence.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">Evidence</p>
          <ul className="space-y-1">
            {hypothesis.evidence.slice(0, 4).map((e, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-slate-400">
                <ChevronRight size={10} className="mt-0.5 shrink-0 text-purple-600" />
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center gap-1.5 text-xs text-slate-600">
        <Shield size={10} className="text-purple-700" />
        <span className="italic">{hypothesis.confidence_rationale}</span>
      </div>
    </div>
  )
}
