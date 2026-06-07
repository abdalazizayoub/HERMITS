import { useWorkbenchStore } from '../../store/workbenchStore'
import KBMatchCard from './KBMatchCard'
import HypothesisCard from './HypothesisCard'
import FixStepList from './FixStepList'
import LoadingSpinner from '../shared/LoadingSpinner'
import { Database, Terminal, Cpu, CheckCircle2, XCircle, RefreshCw, Clock, Wrench } from 'lucide-react'
import type { WorkbenchMode } from '../../store/workbenchStore'
import type { ExecutedStep } from '../../types/agent'
import { formatDistanceToNow, parseISO } from 'date-fns'

const PIPELINE_STAGES: { mode: WorkbenchMode[]; label: string; done: WorkbenchMode[] }[] = [
  { mode: ['phase1_loading'], label: 'Phase 1 — Analysis', done: ['recon_loading', 'phase2_loading', 'reviewing', 'executing', 'manual', 'completing', 'complete', 'validated_failed'] },
  { mode: ['recon_loading'], label: 'SSH Recon', done: ['phase2_loading', 'reviewing', 'executing', 'manual', 'completing', 'complete', 'validated_failed'] },
  { mode: ['phase2_loading'], label: 'Phase 2 — Hypotheses', done: ['reviewing', 'executing', 'manual', 'completing', 'complete', 'validated_failed'] },
  { mode: ['reviewing', 'executing', 'manual'], label: 'Fix Steps', done: ['completing', 'complete', 'validated_failed'] },
  { mode: ['completing'], label: 'Validation & Submit', done: ['complete', 'validated_failed'] },
]

function PipelineProgress({ mode }: { mode: WorkbenchMode }) {
  if (mode === 'idle' || mode === 'error') return null
  return (
    <div className="px-4 pt-3 pb-2 border-b" style={{ borderBottomColor: 'rgba(34,211,238,0.08)' }}>
      <div className="flex items-center gap-1">
        {PIPELINE_STAGES.map((stage, i) => {
          const isActive = stage.mode.includes(mode)
          const isDone = stage.done.includes(mode)
          return (
            <div key={i} className="flex items-center gap-1 flex-1 min-w-0">
              <div className={`h-1 flex-1 rounded-full transition-all duration-500 ${
                isDone
                  ? mode === 'validated_failed' ? 'bg-amber-500' : 'bg-emerald-500'
                  : isActive ? 'bg-cyan-500 pipeline-active' : 'bg-slate-800'
              }`} />
              {i === PIPELINE_STAGES.length - 1 && (
                <div className={`w-2 h-2 rounded-full shrink-0 ${
                  mode === 'complete' ? 'bg-emerald-500' : mode === 'validated_failed' ? 'bg-amber-500' : 'bg-slate-700'
                }`} />
              )}
            </div>
          )
        })}
      </div>
      <div className="mt-1 text-xs text-slate-600 font-mono">
        {mode === 'complete' ? 'Done — Validation passed' :
         mode === 'validated_failed' ? 'Done — Validation failed' :
         mode === 'manual' ? 'Manual shell active' :
         PIPELINE_STAGES.find((s) => s.mode.includes(mode))?.label ?? 'Processing...'}
      </div>
    </div>
  )
}

function Skeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-3 bg-slate-800/80 rounded w-1/3" />
      <div className="h-16 bg-slate-800/60 rounded" />
      <div className="h-3 bg-slate-800/80 rounded w-1/2" />
      <div className="h-12 bg-slate-800/60 rounded" />
      <div className="h-12 bg-slate-800/60 rounded" />
    </div>
  )
}

function ExecutedStepLog({ executedSteps }: { executedSteps: ExecutedStep[] }) {
  if (executedSteps.length === 0) return null
  return (
    <section>
      <div className="flex items-center gap-2 mb-2">
        <Wrench size={11} className="text-amber-500" />
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Executed Commands ({executedSteps.filter(s => s.approved && s.exit_code !== -1).length} applied)
        </p>
      </div>
      <div className="space-y-1">
        {executedSteps.map((step, i) => (
          <div key={i} className={`flex items-start gap-2 px-2 py-1.5 rounded border text-xs font-mono ${
            step.exit_code === -1
              ? 'border-slate-800/40 text-slate-600 bg-transparent'
              : step.exit_code === 0
              ? 'border-emerald-500/20 text-emerald-500 bg-emerald-950/10'
              : 'border-red-500/20 text-red-400 bg-red-950/10'
          }`}>
            <span className="shrink-0 text-slate-600">
              {step.exit_code === -1 ? '↩' : step.exit_code === 0 ? '✓' : '✗'}
            </span>
            <span className="break-all">{step.command}</span>
            <span className="ml-auto shrink-0 text-slate-700 text-xs font-sans">{step.category}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function AIAnalysisPane() {
  const mode = useWorkbenchStore((s) => s.mode)
  const phase1Result = useWorkbenchStore((s) => s.phase1Result)
  const phase2Result = useWorkbenchStore((s) => s.phase2Result)
  const currentStepIndex = useWorkbenchStore((s) => s.currentStepIndex)
  const executedSteps = useWorkbenchStore((s) => s.executedSteps)
  const validationPassed = useWorkbenchStore((s) => s.validationPassed)
  const validationOutput = useWorkbenchStore((s) => s.validationOutput)
  const activeTicketId = useWorkbenchStore((s) => s.activeTicketId)
  const ticketSessions = useWorkbenchStore((s) => s.ticketSessions)
  const reanalyze = useWorkbenchStore((s) => s.reanalyze)

  // Check for a cached/restored session
  const session = activeTicketId ? ticketSessions[activeTicketId] : null

  if (mode === 'idle') {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-700 gap-3">
        <Cpu size={36} className="text-slate-800" />
        <p className="text-xs text-slate-600">Select a ticket to begin AI analysis</p>
      </div>
    )
  }

  const isRestored = session && (mode === 'complete' || mode === 'validated_failed' || mode === 'reviewing')

  return (
    <div className="flex flex-col h-full">
      <PipelineProgress mode={mode} />

      <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 pt-3">

        {/* Restored session banner */}
        {isRestored && session && (
          <div
            className="rounded-lg border px-3 py-2 flex items-center justify-between gap-2"
            style={{
              background: 'rgba(34,211,238,0.04)',
              borderColor: 'rgba(34,211,238,0.2)',
            }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <Clock size={11} className="text-cyan-600 shrink-0" />
              <span className="text-xs text-slate-500 truncate">
                Restored from {formatDistanceToNow(parseISO(session.savedAt), { addSuffix: true })}
              </span>
            </div>
            <button
              onClick={reanalyze}
              className="flex items-center gap-1.5 px-2 py-1 rounded text-xs text-purple-400 border border-purple-500/30 hover:bg-purple-950/30 transition-colors shrink-0"
            >
              <RefreshCw size={10} />
              Re-analyze
            </button>
          </div>
        )}

        {/* Phase 1 loading */}
        {mode === 'phase1_loading' && (
          <>
            <div className="flex items-center gap-2 text-cyan-400 text-xs">
              <LoadingSpinner size={13} />
              Building pillar spec &amp; KB matches...
            </div>
            <Skeleton />
          </>
        )}

        {/* Phase 1 results */}
        {phase1Result && (
          <>
            {phase1Result.kb_matches.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-2">
                  <Database size={11} className="text-purple-500" />
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    KB — {phase1Result.kb_matches.length} match{phase1Result.kb_matches.length !== 1 ? 'es' : ''}
                  </p>
                  {phase1Result.cache_hit && (
                    <span className="text-xs text-cyan-700 font-mono">[cached]</span>
                  )}
                </div>
                <div className="space-y-2">
                  {phase1Result.kb_matches.slice(0, 3).map((m, i) => (
                    <KBMatchCard key={m.entry_id} match={m} index={i} />
                  ))}
                </div>
              </section>
            )}

            <section>
              <div className="flex items-center gap-2 mb-2">
                <Terminal size={11} className="text-cyan-600" />
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Validation Pillars
                </p>
              </div>
              <div className="space-y-1">
                {(['service_state_cmd', 'functional_impact_cmd', 'durability_cmd'] as const).map((key) => (
                  <code
                    key={key}
                    className="block text-xs font-mono bg-slate-900 text-cyan-400 px-2.5 py-1.5 rounded border border-slate-800/80"
                  >
                    {phase1Result.pillar_spec[key]}
                  </code>
                ))}
                <p className="text-xs text-slate-600 italic pt-1">{phase1Result.pillar_spec.definition_of_done}</p>
              </div>
            </section>
          </>
        )}

        {/* Recon / Phase 2 loading */}
        {(mode === 'recon_loading' || mode === 'phase2_loading') && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-cyan-400 text-xs">
              <LoadingSpinner size={13} />
              {mode === 'recon_loading' ? 'Running SSH reconnaissance...' : 'Phase 2 — generating hypotheses with Gemini...'}
            </div>
            <Skeleton />
          </div>
        )}

        {/* Phase 2 results */}
        {phase2Result && (
          <>
            <HypothesisCard hypothesis={phase2Result.hypothesis} />
            <FixStepList
              steps={phase2Result.hypothesis.fix_steps}
              safetyResults={phase2Result.safety_results}
              currentIndex={currentStepIndex}
              executedCount={executedSteps.filter((s) => s.category === 'fix_step').length}
            />
          </>
        )}

        {/* Executed steps log (manual mode or after completion) */}
        {(mode === 'manual' || mode === 'complete' || mode === 'validated_failed') && (
          <ExecutedStepLog executedSteps={executedSteps} />
        )}

        {/* Validation result card */}
        {(mode === 'complete' || mode === 'validated_failed') && validationPassed !== null && (
          <div className={`rounded-xl border p-4 space-y-2 ${
            validationPassed
              ? 'border-emerald-500/40 bg-emerald-950/20'
              : 'border-amber-500/40 bg-amber-950/20'
          }`}>
            <div className="flex items-center gap-2">
              {validationPassed ? (
                <CheckCircle2 size={18} className="text-emerald-400" style={{ filter: 'drop-shadow(0 0 6px #34d399)' }} />
              ) : (
                <XCircle size={18} className="text-amber-400" />
              )}
              <p className={`text-sm font-bold ${validationPassed ? 'text-emerald-400' : 'text-amber-400'}`}>
                Validation {validationPassed ? 'PASSED' : 'FAILED'}
              </p>
            </div>
            {validationOutput && (
              <pre className="text-xs text-slate-500 leading-relaxed whitespace-pre-wrap break-words max-h-32 overflow-y-auto bg-slate-950/60 rounded p-2 border border-slate-800/60 font-mono">
                {validationOutput.trim()}
              </pre>
            )}
            {validationPassed && (
              <p className="text-xs text-emerald-600">Activity logged to ERP. Ticket marked DONE.</p>
            )}
            {!validationPassed && (
              <p className="text-xs text-amber-600">Ticket remains OPEN. Use the manual shell to attempt further fixes.</p>
            )}
          </div>
        )}

        {mode === 'error' && (
          <div className="rounded-lg border border-red-500/40 bg-red-950/20 p-3">
            <p className="text-red-400 text-xs">Analysis error — check terminal for details</p>
          </div>
        )}
      </div>
    </div>
  )
}
