import { useState } from 'react'
import { BarChart3, Zap, RotateCcw, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react'
import TicketList from '../tickets/TicketList'
import WorkbenchPanel from '../workbench/WorkbenchPanel'
import AnalysisModal from '../analysis/AnalysisModal'
import { resetEnvironment } from '../../api/activities'
import { useQueryClient } from '@tanstack/react-query'
import { useWorkbenchStore } from '../../store/workbenchStore'

type ResetState = 'idle' | 'confirming' | 'loading' | 'done' | 'error'

export default function AppShell() {
  const [showAnalysis, setShowAnalysis] = useState(false)
  const [resetState, setResetState] = useState<ResetState>('idle')
  const qc = useQueryClient()
  const reset = useWorkbenchStore((s) => s.reset)

  async function handleReset() {
    if (resetState === 'idle') { setResetState('confirming'); return }
    if (resetState !== 'confirming') return
    setResetState('loading')
    try {
      await resetEnvironment()
      reset()
      qc.invalidateQueries({ queryKey: ['tickets'] })
      setResetState('done')
      setTimeout(() => setResetState('idle'), 3000)
    } catch {
      setResetState('error')
      setTimeout(() => setResetState('idle'), 3000)
    }
  }

  const resetLabel = {
    idle: 'Reset ERP',
    confirming: 'Confirm Reset?',
    loading: 'Resetting...',
    done: 'Reset Done!',
    error: 'Reset Failed',
  }[resetState]

  return (
    <div className="flex flex-col h-full bg-slate-950">
      {/* Top navigation bar */}
      <header
        className="flex items-center justify-between px-4 py-2 shrink-0 glass border-b"
        style={{ borderBottomColor: 'rgba(34,211,238,0.18)' }}
      >
        <div className="flex items-center gap-3">
          <Zap size={18} className="text-cyan-400" style={{ filter: 'drop-shadow(0 0 6px #22d3ee)' }} />
          <span className="text-sm font-bold gradient-text tracking-tight">HERMITS</span>
          <span className="text-xs text-slate-600 font-mono">// AI Service Desk Autopilot</span>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/25 ml-1">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs text-cyan-400 font-mono">LIVE</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAnalysis(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-950/50 hover:bg-purple-900/60 text-purple-300 hover:text-purple-200 text-xs font-medium transition-all border border-purple-700/40 hover:border-purple-500/60 hover:shadow-glow-purple"
          >
            <BarChart3 size={13} />
            Monthly Analysis
          </button>

          <button
            onClick={handleReset}
            disabled={resetState === 'loading' || resetState === 'done'}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border disabled:cursor-not-allowed ${
              resetState === 'confirming'
                ? 'bg-orange-950/60 text-orange-300 border-orange-500/60 shadow-glow-orange'
                : resetState === 'done'
                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/60'
                : resetState === 'error'
                ? 'bg-red-950/60 text-red-300 border-red-500/60'
                : 'bg-slate-800/60 hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 border-slate-700/60 hover:border-slate-600'
            }`}
          >
            {resetState === 'loading' ? (
              <Loader2 size={12} className="animate-spin" />
            ) : resetState === 'done' ? (
              <CheckCircle2 size={12} />
            ) : resetState === 'confirming' ? (
              <AlertTriangle size={12} />
            ) : (
              <RotateCcw size={12} />
            )}
            {resetLabel}
          </button>

          {resetState === 'confirming' && (
            <button
              onClick={() => setResetState('idle')}
              className="px-2 py-1.5 rounded-lg text-xs text-slate-500 hover:text-slate-300 border border-slate-700 hover:border-slate-600 transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        <div className="w-72 shrink-0">
          <TicketList />
        </div>
        <div className="flex-1 min-w-0">
          <WorkbenchPanel />
        </div>
      </div>

      {showAnalysis && <AnalysisModal onClose={() => setShowAnalysis(false)} />}
    </div>
  )
}
