import type { Hypothesis } from '../../types/agent'
import { Lightbulb, ChevronRight } from 'lucide-react'

export default function HypothesisCard({ hypothesis }: { hypothesis: Hypothesis }) {
  return (
    <div className="rounded-lg border border-blue-800/50 bg-blue-950/20 p-3 space-y-2">
      <div className="flex items-start gap-2">
        <Lightbulb size={14} className="text-blue-400 mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-semibold text-slate-100">{hypothesis.hypothesis_title}</p>
          <p className="text-xs text-slate-400 mt-0.5">{hypothesis.root_cause_explanation}</p>
        </div>
      </div>

      {hypothesis.evidence.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 mb-1">Evidence</p>
          <ul className="space-y-0.5">
            {hypothesis.evidence.map((e, i) => (
              <li key={i} className="flex items-start gap-1 text-xs text-slate-400">
                <ChevronRight size={10} className="mt-0.5 shrink-0 text-slate-600" />
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-slate-500 italic">{hypothesis.confidence_rationale}</p>
    </div>
  )
}
