import type { KBMatch } from '../../types/kb'
import { CheckCircle, XCircle, Clock } from 'lucide-react'

export default function KBMatchCard({ match, index }: { match: KBMatch; index: number }) {
  const pct = Math.round(match.similarity_score * 100)

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400">KB Match #{index + 1}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-blue-400">{pct}% similar</span>
          {match.validation_passed ? (
            <CheckCircle size={12} className="text-emerald-400" />
          ) : (
            <XCircle size={12} className="text-red-400" />
          )}
        </div>
      </div>

      <p className="text-sm text-slate-200">{match.root_cause}</p>

      {match.fix_commands.length > 0 && (
        <div className="space-y-1">
          {match.fix_commands.slice(0, 3).map((cmd, i) => (
            <code key={i} className="block text-xs font-mono bg-slate-800 text-emerald-300 px-2 py-1 rounded">
              {cmd}
            </code>
          ))}
        </div>
      )}

      <div className="flex items-center gap-1 text-xs text-slate-500">
        <Clock size={10} />
        Resolved in {match.resolution_time_minutes} min
        {match.service_hint && <span className="ml-2 font-mono">[{match.service_hint}]</span>}
      </div>
    </div>
  )
}
