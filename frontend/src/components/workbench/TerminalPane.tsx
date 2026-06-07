import { useRef, useEffect } from 'react'
import { useWorkbenchStore } from '../../store/workbenchStore'
import { useTerminal } from '../../hooks/useTerminal'
import { executeCommand } from '../../api/agent'

export default function TerminalPane() {
  const containerRef = useRef<HTMLDivElement>(null)
  const { writeLine, enableInput, setReadOnly, fit } = useTerminal(containerRef as React.RefObject<HTMLDivElement>)
  const mode = useWorkbenchStore((s) => s.mode)
  const activeTicketId = useWorkbenchStore((s) => s.activeTicketId)
  const addExecutedStep = useWorkbenchStore((s) => s.addExecutedStep)
  const inputCleanupRef = useRef<(() => void) | null>(null)

  // Toggle manual input mode
  useEffect(() => {
    if (mode === 'manual' && activeTicketId) {
      const cleanup = enableInput(async (cmd) => {
        try {
          const result = await executeCommand({
            ticket_id: activeTicketId,
            command: cmd,
            category: 'manual',
          })

          if (result.blocked) {
            writeLine(`\x1b[31m[BLOCKED] ${result.block_reason}\x1b[0m`, 'error')
            return
          }
          if (result.stdout) writeLine(result.stdout)
          if (result.stderr) writeLine(result.stderr, 'error')

          addExecutedStep({
            command: cmd,
            output: result.stdout + result.stderr,
            exit_code: result.exit_code,
            approved: true,
            category: 'manual',
            timestamp: new Date().toISOString(),
          })
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err)
          writeLine(`\x1b[31m[ERROR] ${msg}\x1b[0m`, 'error')
        }
      })
      inputCleanupRef.current = cleanup ?? null
    } else {
      inputCleanupRef.current?.()
      inputCleanupRef.current = null
      setReadOnly(true)
    }
  }, [mode, activeTicketId, enableInput, setReadOnly, writeLine, addExecutedStep])

  // Fit on resize
  useEffect(() => {
    const ro = new ResizeObserver(() => fit())
    if (containerRef.current) ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [fit])

  return (
    <div className="flex flex-col h-full bg-slate-950">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-800 bg-slate-900">
        <span className="text-xs text-slate-500 font-mono">terminal</span>
        {mode === 'manual' && (
          <span className="text-xs text-blue-400 font-mono animate-pulse">● manual input</span>
        )}
      </div>
      <div
        ref={containerRef}
        className="flex-1 min-h-0 p-2"
        style={{ fontFamily: 'JetBrains Mono, monospace' }}
      />
    </div>
  )
}
