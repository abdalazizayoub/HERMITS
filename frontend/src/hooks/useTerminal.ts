import { useEffect, useRef, useCallback } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import { useWorkbenchStore } from '../store/workbenchStore'

const COLORS = {
  info: '',
  success: '\x1b[32m',
  error: '\x1b[31m',
  system: '\x1b[36m',
  warn: '\x1b[33m',
}

export function useTerminal(containerRef: React.RefObject<HTMLDivElement>) {
  const terminalRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const setTerminalRef = useWorkbenchStore((s) => s.setTerminalRef)

  const writeLine = useCallback((line: string, type: 'info' | 'success' | 'error' | 'system' | 'warn' = 'info') => {
    const term = terminalRef.current
    if (!term) return
    const color = COLORS[type]
    const reset = color ? '\x1b[0m' : ''
    term.writeln(`${color}${line}${reset}`)
  }, [])

  useEffect(() => {
    if (!containerRef.current || terminalRef.current) return

    const term = new Terminal({
      theme: {
        background: '#020617',
        foreground: '#e2e8f0',
        cursor: '#38bdf8',
        selectionBackground: '#1e40af',
        black: '#020617',
        green: '#22c55e',
        red: '#ef4444',
        cyan: '#22d3ee',
        yellow: '#eab308',
        white: '#e2e8f0',
      },
      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
      fontSize: 12,
      lineHeight: 1.4,
      scrollback: 5000,
      cursorBlink: true,
      disableStdin: true,
    })

    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()
    term.loadAddon(fitAddon)
    term.loadAddon(webLinksAddon)
    term.open(containerRef.current)
    fitAddon.fit()

    terminalRef.current = term
    fitAddonRef.current = fitAddon

    term.writeln('\x1b[36m╔══════════════════════════════════════════╗\x1b[0m')
    term.writeln('\x1b[36m║       HERMITS — Incident Response        ║\x1b[0m')
    term.writeln('\x1b[36m╚══════════════════════════════════════════╝\x1b[0m')
    term.writeln('\x1b[90mSelect a ticket to begin...\x1b[0m')

    const ro = new ResizeObserver(() => fitAddon.fit())
    ro.observe(containerRef.current)

    setTerminalRef(writeLine)

    return () => {
      ro.disconnect()
    }
  }, [containerRef, writeLine, setTerminalRef])

  const setReadOnly = useCallback((readOnly: boolean) => {
    const term = terminalRef.current
    if (!term) return
    term.options.disableStdin = readOnly
  }, [])

  const enableInput = useCallback((onSubmit: (cmd: string) => void) => {
    const term = terminalRef.current
    if (!term) return

    term.options.disableStdin = false
    let buffer = ''

    term.write('\x1b[32m$ \x1b[0m')

    const disposable = term.onKey(({ key, domEvent }) => {
      if (domEvent.keyCode === 13) {
        const cmd = buffer.trim()
        buffer = ''
        term.writeln('')
        if (cmd) onSubmit(cmd)
        term.write('\x1b[32m$ \x1b[0m')
      } else if (domEvent.keyCode === 8) {
        if (buffer.length > 0) {
          buffer = buffer.slice(0, -1)
          term.write('\b \b')
        }
      } else if (!domEvent.ctrlKey && !domEvent.altKey && key.length === 1) {
        buffer += key
        term.write(key)
      }
    })

    return () => {
      disposable.dispose()
      term.options.disableStdin = true
    }
  }, [])

  const clear = useCallback(() => {
    terminalRef.current?.clear()
  }, [])

  const fit = useCallback(() => {
    fitAddonRef.current?.fit()
  }, [])

  return { writeLine, setReadOnly, enableInput, clear, fit }
}
