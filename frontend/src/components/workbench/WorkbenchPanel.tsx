import { useEffect, useRef } from 'react'
import { useWorkbenchStore } from '../../store/workbenchStore'
import { useTicketDetail } from '../../hooks/useTicketDetail'
import { usePhase1 } from '../../hooks/usePhase1'
import { usePhase2 } from '../../hooks/usePhase2'
import { runRecon } from '../../api/agent'
import TicketHeader from './TicketHeader'
import AIAnalysisPane from './AIAnalysisPane'
import TerminalPane from './TerminalPane'
import ActionBar from './ActionBar'
import LoadingSpinner from '../shared/LoadingSpinner'
import { Inbox, Zap } from 'lucide-react'

export default function WorkbenchPanel() {
  const activeTicketId = useWorkbenchStore((s) => s.activeTicketId)
  const mode = useWorkbenchStore((s) => s.mode)
  const phase1Result = useWorkbenchStore((s) => s.phase1Result)
  const reanalyzeKey = useWorkbenchStore((s) => s.reanalyzeKey)
  const consumeForceRefresh = useWorkbenchStore((s) => s.consumeForceRefresh)
  const setReconOutput = useWorkbenchStore((s) => s.setReconOutput)
  const writeToTerminal = useWorkbenchStore((s) => s.writeToTerminal)

  const { data: ticket } = useTicketDetail(activeTicketId)
  const { run: runPhase1 } = usePhase1()
  const { run: runPhase2 } = usePhase2()

  // Composite key: ticket + reanalyzeKey — prevents double-fire in StrictMode
  // and correctly re-fires when reanalyze() is called on the same ticket.
  const lastStartedRef = useRef<string | null>(null)

  // Phase 1 trigger — only runs if mode is phase1_loading (not restored sessions)
  useEffect(() => {
    if (!activeTicketId || mode !== 'phase1_loading') return
    const runKey = `${activeTicketId}-${reanalyzeKey}`
    if (lastStartedRef.current === runKey) return
    lastStartedRef.current = runKey
    // Consume the force-refresh flag set by reanalyze() — passes it to backend
    // so the prewarm cache is bypassed and fresh analysis is generated.
    const forceRefresh = consumeForceRefresh()
    runPhase1(activeTicketId, forceRefresh)
  }, [activeTicketId, mode, reanalyzeKey, consumeForceRefresh, runPhase1])

  // Recon + Phase 2 — only runs when explicitly in recon_loading
  useEffect(() => {
    if (mode !== 'recon_loading' || !activeTicketId) return

    async function doReconAndPhase2() {
      writeToTerminal('\r\n\x1b[36m[HERMITS] Running SSH reconnaissance...\x1b[0m\r\n', 'system')
      try {
        const recon = await runRecon(activeTicketId!)
        setReconOutput(recon)

        const sections = ['logs', 'service_statuses', 'disk_usage', 'network', 'database']
        for (const key of sections) {
          const val = recon[key]
          if (val) {
            writeToTerminal(`\r\n\x1b[33m── ${key.replace('_', ' ')} ──\x1b[0m\r\n`, 'warn')
            const lines = val.split('\n').slice(0, 15)
            for (const line of lines) {
              if (line.trim()) writeToTerminal(line)
            }
          }
        }

        writeToTerminal('\r\n\x1b[32m[HERMITS] Recon complete.\x1b[0m\r\n', 'success')
        await runPhase2(activeTicketId!, recon, phase1Result)
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        writeToTerminal(`\x1b[31m[ERROR] Recon failed: ${msg}\x1b[0m\r\n`, 'error')
        await runPhase2(activeTicketId!, {}, phase1Result)
      }
    }

    doReconAndPhase2()
  }, [mode, activeTicketId, phase1Result, setReconOutput, writeToTerminal, runPhase2])

  if (!activeTicketId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="relative">
          <Inbox size={48} className="text-slate-800" />
          <Zap size={16} className="text-cyan-700 absolute -top-1 -right-1" />
        </div>
        <div className="text-center">
          <p className="text-sm text-slate-600 font-medium">No ticket selected</p>
          <p className="text-xs text-slate-700 mt-1">Pick a ticket from the left panel to begin</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {ticket ? (
        <TicketHeader ticket={ticket} />
      ) : (
        <div
          className="px-4 py-3 border-b flex items-center gap-2 text-slate-600 text-xs glass"
          style={{ borderBottomColor: 'rgba(34,211,238,0.12)' }}
        >
          <LoadingSpinner size={13} />
          Loading ticket...
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        <div
          className="w-[44%] shrink-0 border-r overflow-y-auto"
          style={{ borderRightColor: 'rgba(34,211,238,0.1)' }}
        >
          <AIAnalysisPane />
        </div>
        <div className="flex-1 min-w-0">
          <TerminalPane />
        </div>
      </div>

      <ActionBar />
    </div>
  )
}
