import { useCallback } from 'react'
import { startPhase1, streamPhase1Status, runPhase1Direct } from '../api/ai'
import { useWorkbenchStore } from '../store/workbenchStore'
import type { Phase1Result } from '../types/agent'

export function usePhase1() {
  const { setPhase1Result, setError, writeToTerminal, setMode } = useWorkbenchStore()

  const run = useCallback(async (ticketId: number, forceRefresh = false, technicianId = 'default') => {
    const refreshLabel = forceRefresh ? ' \x1b[33m(force-refresh)\x1b[0m' : ''
    writeToTerminal(`\r\n\x1b[36m[HERMITS] Starting Phase 1 analysis...${refreshLabel}\x1b[0m\r\n`, 'system')

    let succeeded = false

    try {
      // Try SSE streaming first
      const { job_id } = await startPhase1(ticketId, technicianId, forceRefresh)
      const es = streamPhase1Status(job_id)

      await new Promise<void>((resolve, reject) => {
        es.addEventListener('status', () => {
          writeToTerminal('\x1b[36m[HERMITS] Generating pillar spec and KB matches...\x1b[0m\r\n', 'system')
        })

        es.addEventListener('done', (e: MessageEvent) => {
          try {
            const payload = JSON.parse(e.data)
            const result: Phase1Result = payload.data ?? payload
            setPhase1Result(result)
            writeToTerminal('\x1b[32m[HERMITS] Phase 1 complete.\x1b[0m\r\n', 'success')
            if (result.cache_hit) {
              writeToTerminal('\x1b[36m[HERMITS] Result served from pre-warm cache.\x1b[0m\r\n', 'system')
            }
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
      succeeded = true
    } catch {
      // SSE not available — fall back to direct POST
      writeToTerminal('\x1b[36m[HERMITS] Running Phase 1 (direct)...\x1b[0m\r\n', 'system')
      try {
        const result = await runPhase1Direct(ticketId, technicianId, forceRefresh)
        setPhase1Result(result)
        writeToTerminal('\x1b[32m[HERMITS] Phase 1 complete.\x1b[0m\r\n', 'success')
        succeeded = true
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        setError(`Phase 1 failed: ${msg}`)
        writeToTerminal(`\x1b[31m[ERROR] Phase 1 failed: ${msg}\x1b[0m\r\n`, 'error')
      }
    }

    if (succeeded) setMode('recon_loading')
  }, [setPhase1Result, setError, writeToTerminal, setMode])

  return { run }
}
