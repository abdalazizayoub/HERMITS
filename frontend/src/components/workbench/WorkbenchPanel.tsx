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
import { Inbox } from 'lucide-react'

export default function WorkbenchPanel() {
  const activeTicketId = useWorkbenchStore((s) => s.activeTicketId)
  const mode = useWorkbenchStore((s) => s.mode)
  const phase1Result = useWorkbenchStore((s) => s.phase1Result)
  const setReconOutput = useWorkbenchStore((s) => s.setReconOutput)
  const writeToTerminal = useWorkbenchStore((s) => s.writeToTerminal)

  const { data: ticket } = useTicketDetail(activeTicketId)
  const { run: runPhase1 } = usePhase1()
  const { run: runPhase2 } = usePhase2()

  // Ref to track which ticket we last started analysis for (prevents double-fire in StrictMode)
  const lastStartedRef = useRef<number | null>(null)

  useEffect(() => {
    if (!activeTicketId || mode !== 'phase1_loading') return
    if (lastStartedRef.current === activeTicketId) return
    lastStartedRef.current = activeTicketId

    runPhase1(activeTicketId)
  }, [activeTicketId, mode, runPhase1])

  // When Phase 1 done → run recon → Phase 2
  useEffect(() => {
    if (mode !== 'recon_loading' || !activeTicketId) return

    async function doReconAndPhase2() {
      writeToTerminal('\r\n\x1b[36m[HERMITS] Running SSH reconnaissance...\x1b[0m\r\n', 'system')
      try {
        const recon = await runRecon(activeTicketId!)
        setReconOutput(recon)

        // Write recon sections to terminal
        const sections = ['logs', 'service_statuses', 'disk_usage', 'network', 'database']
        for (const key of sections) {
          const val = recon[key]
          if (val) {
            writeToTerminal(`\r\n\x1b[33m── ${key.replace('_', ' ')} ──\x1b[0m\r\n`, 'warn')
            const lines = val.split('\n').slice(0, 20)
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
        // Still try Phase 2 with empty recon
        await runPhase2(activeTicketId!, {}, phase1Result)
      }
    }

    doReconAndPhase2()
  }, [mode, activeTicketId, phase1Result, setReconOutput, writeToTerminal, runPhase2])

  if (!activeTicketId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-3">
        <Inbox size={40} />
        <p className="text-sm text-slate-500">Select a ticket from the left panel</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Ticket header */}
      {ticket ? (
        <TicketHeader ticket={ticket} />
      ) : (
        <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2 text-slate-500 text-sm">
          <LoadingSpinner size={14} />
          Loading ticket...
        </div>
      )}

      {/* Main split: analysis + terminal */}
      <div className="flex-1 flex min-h-0">
        {/* AI Analysis pane */}
        <div className="w-[45%] border-r border-slate-800 overflow-y-auto">
          <AIAnalysisPane />
        </div>

        {/* Terminal pane */}
        <div className="flex-1 min-w-0">
          <TerminalPane />
        </div>
      </div>

      {/* Action bar */}
      <ActionBar />
    </div>
  )
}
