import { useWorkbenchStore } from '../../store/workbenchStore'
import KBMatchCard from './KBMatchCard'
import HypothesisCard from './HypothesisCard'
import FixStepList from './FixStepList'
import LoadingSpinner from '../shared/LoadingSpinner'
import { Database, Terminal, Cpu } from 'lucide-react'

function Skeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 bg-slate-800 rounded w-1/3" />
      <div className="h-20 bg-slate-800 rounded" />
      <div className="h-4 bg-slate-800 rounded w-1/2" />
      <div className="h-16 bg-slate-800 rounded" />
      <div className="h-16 bg-slate-800 rounded" />
    </div>
  )
}

export default function AIAnalysisPane() {
  const mode = useWorkbenchStore((s) => s.mode)
  const phase1Result = useWorkbenchStore((s) => s.phase1Result)
  const phase2Result = useWorkbenchStore((s) => s.phase2Result)
  const currentStepIndex = useWorkbenchStore((s) => s.currentStepIndex)
  const executedSteps = useWorkbenchStore((s) => s.executedSteps)

  if (mode === 'idle') {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-3">
        <Cpu size={32} />
        <p className="text-sm">Select a ticket to start analysis</p>
      </div>
    )
  }

  if (mode === 'phase1_loading') {
    return (
      <div className="p-4 space-y-4">
        <div className="flex items-center gap-2 text-blue-400 text-sm">
          <LoadingSpinner size={14} />
          Phase 1 — Building pillar spec & KB matches...
        </div>
        <Skeleton />
      </div>
    )
  }

  return (
    <div className="p-4 space-y-5 overflow-y-auto h-full">
      {/* Phase 1 results */}
      {phase1Result && (
        <>
          {phase1Result.kb_matches.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-2">
                <Database size={12} className="text-slate-500" />
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Knowledge Base Matches
                </p>
              </div>
              <div className="space-y-2">
                {phase1Result.kb_matches.slice(0, 3).map((m, i) => (
                  <KBMatchCard key={m.entry_id} match={m} index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Pillar spec */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <Terminal size={12} className="text-slate-500" />
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Validation Pillars
              </p>
            </div>
            <div className="space-y-1.5">
              {(['service_state_cmd', 'functional_impact_cmd', 'durability_cmd'] as const).map((key) => (
                <code key={key} className="block text-xs font-mono bg-slate-800 text-cyan-300 px-2 py-1.5 rounded">
                  {phase1Result.pillar_spec[key]}
                </code>
              ))}
              <p className="text-xs text-slate-500 italic">{phase1Result.pillar_spec.definition_of_done}</p>
            </div>
          </section>
        </>
      )}

      {/* Recon / Phase 2 loading */}
      {(mode === 'recon_loading' || mode === 'phase2_loading') && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-blue-400 text-sm">
            <LoadingSpinner size={14} />
            {mode === 'recon_loading' ? 'Running SSH reconnaissance...' : 'Phase 2 — Generating hypotheses...'}
          </div>
          <Skeleton />
        </div>
      )}

      {/* Phase 2 results */}
      {phase2Result && (
        <>
          <section>
            <HypothesisCard hypothesis={phase2Result.hypothesis} />
          </section>

          <FixStepList
            steps={phase2Result.hypothesis.fix_steps}
            safetyResults={phase2Result.safety_results}
            currentIndex={currentStepIndex}
            executedCount={executedSteps.filter((s) => s.category === 'fix_step').length}
          />
        </>
      )}

      {mode === 'complete' && (
        <div className="rounded-lg border border-emerald-700 bg-emerald-950/20 p-4 text-center">
          <p className="text-emerald-400 font-semibold">✓ Ticket resolved and closed</p>
        </div>
      )}

      {mode === 'error' && (
        <div className="rounded-lg border border-red-700 bg-red-950/20 p-3">
          <p className="text-red-400 text-sm">Analysis error — check terminal for details</p>
        </div>
      )}
    </div>
  )
}
