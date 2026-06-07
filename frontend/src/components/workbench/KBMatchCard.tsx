import type { KBMatch } from '../../types/kb'
import { CheckCircle2, XCircle, Clock, BookOpen } from 'lucide-react'

export default function KBMatchCard({ match, index }: { match: KBMatch; index: number }) {
  const pct = Math.round(match.similarity_score * 100)
  const isHighMatch = pct >= 70

  return (
    <div className={`rounded-lg border p-3 space-y-2 ${isHighMatch ? 'border-purple-500/30 bg-purple-950/15' : 'border-slate-800 bg-slate-900/50'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <BookOpen size={10} className={isHighMatch ? 'text-purple-500' : 'text-slate-600'} />
          <span className="text-xs font-semibold text-slate-500">KB #{index + 1}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div className="w-12 h-1 rounded-full bg-slate-800 overflow-hidden">
              <div
                className={`h-full rounded-full ${isHighMatch ? 'bg-purple-500' : 'bg-slate-600'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className={`text-xs font-mono font-bold ${isHighMatch ? 'text-purple-400' : 'text-slate-500'}`}>{pct}%</span>
          </div>
          {match.validation_passed ? (
            <CheckCircle2 size={11} className="text-emerald-400" />
          ) : (
            <XCircle size={11} className="text-red-500" />
          )}
        </div>
      </div>

      <p className="text-xs text-slate-300 leading-relaxed">{match.root_cause}</p>

      {match.fix_commands.length > 0 && (
        <div className="space-y-1">
          {match.fix_commands.slice(0, 2).map((cmd, i) => (
            <code key={i} className="block text-xs font-mono bg-slate-950 text-emerald-500 px-2 py-1 rounded border border-slate-800/60">
              {cmd}
            </code>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3 text-xs text-slate-600">
        <span className="flex items-center gap-1">
          <Clock size={9} />
          {match.resolution_time_minutes} min
        </span>
        {match.service_hint && <span className="font-mono">[{match.service_hint}]</span>}
      </div>
    </div>
  )
}
