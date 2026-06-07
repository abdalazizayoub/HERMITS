import { useCallback } from 'react'
import { startPhase2, streamPhase2Status, runPhase2Direct } from '../api/ai'
import { useWorkbenchStore } from '../store/workbenchStore'
import type { Phase1Result, Phase2Result, ReconOutput } from '../types/agent'

export function usePhase2() {
  const { setPhase2Result, setError, setMode, writeToTerminal } = useWorkbenchStore()

  const run = useCallback(async (
    ticketId: number,
    reconOutput: ReconOutput | Record<string, never>,
    p1Result: Phase1Result | null,
    technicianId = 'default',
  ) => {
    setMode('phase2_loading')
    writeToTerminal('\r\n\x1b[36m[HERMITS] Starting Phase 2 — generating hypotheses...\x1b[0m\r\n', 'system')

    const pillarBaseline = p1Result?.pillar_baseline ?? null

    try {
      const { job_id } = await startPhase2(ticketId, reconOutput as Record<string, string | undefined>, pillarBaseline, technicianId)
      const es = streamPhase2Status(job_id)

      await new Promise<void>((resolve, reject) => {
        es.addEventListener('status', () => {
          writeToTerminal('\x1b[36m[HERMITS] Analyzing recon data with Gemini...\x1b[0m\r\n', 'system')
        })

        es.addEventListener('done', (e: MessageEvent) => {
          try {
            const payload = JSON.parse(e.data)
            const result: Phase2Result = payload.data ?? payload
            setPhase2Result(result)
            setMode('reviewing')
            writeToTerminal('\x1b[32m[HERMITS] Phase 2 complete — hypothesis ready.\x1b[0m\r\n', 'success')
            resolve()
          } catch (err) {
            reject(err)
          } finally {
            es.close()
          }
        })

        es.addEventListener('error', (e) => {
          es.close()
          reject(new Error(`SSE error: ${JSON.stringify(e)}`))
        })
      })
    } catch {
      writeToTerminal('\x1b[36m[HERMITS] Running Phase 2 (direct)...\x1b[0m\r\n', 'system')
      try {
        const result = await runPhase2Direct(ticketId, reconOutput as Record<string, string | undefined>, pillarBaseline, technicianId)
        setPhase2Result(result)
        setMode('reviewing')
        writeToTerminal('\x1b[32m[HERMITS] Phase 2 complete — hypothesis ready.\x1b[0m\r\n', 'success')
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        setError(`Phase 2 failed: ${msg}`)
        writeToTerminal(`\x1b[31m[ERROR] Phase 2 failed: ${msg}\x1b[0m\r\n`, 'error')
      }
    }
  }, [setPhase2Result, setError, setMode, writeToTerminal])

  return { run }
}
