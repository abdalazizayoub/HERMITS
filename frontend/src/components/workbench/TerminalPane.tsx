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
  const prevModeRef = useRef<string>('')

  useEffect(() => {
    const prevMode = prevModeRef.current
    prevModeRef.current = mode

    if (mode === 'manual' && activeTicketId) {
      // Print hint only when first entering manual mode
      if (prevMode !== 'manual') {
        writeLine('\r\n\x1b[36m╔══════════════════════════════════════════╗\x1b[0m', 'system')
        writeLine('\x1b[36m║   Manual Shell — type commands below     ║\x1b[0m', 'system')
        writeLine('\x1b[36m║   All commands are logged & audited      ║\x1b[0m', 'system')
        writeLine('\x1b[36m╚══════════════════════════════════════════╝\x1b[0m', 'system')
        writeLine('\x1b[90mSafety layer active — destructive commands will be blocked.\x1b[0m', 'system')
        writeLine('', 'info')
      }

      const cleanup = enableInput(async (cmd) => {
        try {
          const result = await executeCommand({
            ticket_id: activeTicketId,
            command: cmd,
            category: 'manual',
          })

          if (result.blocked) {
            writeLine(`\x1b[31m[BLOCKED] ${result.reason ?? 'Command blocked by safety layer'}\x1b[0m`, 'error')
            if (result.warnings?.length) {
              for (const w of result.warnings) {
                writeLine(`\x1b[33m[WARN] ${w}\x1b[0m`, 'warn')
              }
            }
            return
          }

          if (result.stdout) writeLine(result.stdout)
          if (result.stderr) writeLine(result.stderr, 'error')

          const exitLabel = result.exit_code === 0
            ? `\x1b[32m[exit 0]\x1b[0m`
            : `\x1b[31m[exit ${result.exit_code}]\x1b[0m`
          writeLine(exitLabel)

          addExecutedStep({
            command: cmd,
            output: result.stdout + result.stderr,
            exit_code: result.exit_code,
            approved: result.exit_code === 0,
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

  useEffect(() => {
    const ro = new ResizeObserver(() => fit())
    if (containerRef.current) ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [fit])

  const modeLabel = {
    manual: '● shell active',
    executing: '● running cmd',
    completing: '● validating',
  }[mode as string]

  const modeColor = mode === 'manual' ? 'text-cyan-400' : mode === 'completing' ? 'text-amber-400' : 'text-emerald-400'

  return (
    <div className="flex flex-col h-full bg-slate-950">
      <div
        className="flex items-center justify-between px-3 py-1.5 border-b glass"
        style={{ borderBottomColor: 'rgba(34,211,238,0.12)' }}
      >
        <span className="text-xs text-slate-600 font-mono">terminal</span>
        {modeLabel && (
          <span className={`text-xs font-mono pipeline-active ${modeColor}`}>{modeLabel}</span>
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
