import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, Terminal, Loader2 } from 'lucide-react'
import { useWorkbenchStore } from '../../store/workbenchStore'
import { executeCommand } from '../../api/agent'
import { runValidation } from '../../api/agent'
import { completeTicket } from '../../api/ai'
import { submitActivity } from '../../api/activities'
import { updateTicketStatus } from '../../api/tickets'

export default function ActionBar() {
  const qc = useQueryClient()
  const {
    mode,
    activeTicketId,
    phase1Result,
    phase2Result,
    currentStepIndex,
    executedSteps,
    sessionStartTime,
    setMode,
    advanceStep,
    addExecutedStep,
    writeToTerminal,
    abort,
  } = useWorkbenchStore()

  const canAccept = mode === 'reviewing' && phase2Result !== null
  const canAbort = ['phase1_loading', 'recon_loading', 'phase2_loading', 'reviewing', 'executing', 'manual'].includes(mode)
  const canManual = ['reviewing', 'manual'].includes(mode)

  const currentStep = phase2Result?.hypothesis.fix_steps[currentStepIndex]
  const safety = phase2Result?.safety_results[currentStepIndex]
  const isBlocked = safety && !safety.is_safe

  async function handleAccept() {
    if (!activeTicketId || !currentStep || isBlocked) return
    setMode('executing')

    writeToTerminal(`\r\n\x1b[36m$ ${currentStep.command}\x1b[0m\r\n`, 'system')

    try {
      const result = await executeCommand({
        ticket_id: activeTicketId,
        command: currentStep.command,
        category: 'fix_step',
      })

      if (result.blocked) {
        writeToTerminal(`\x1b[31m[BLOCKED] ${result.block_reason}\x1b[0m\r\n`, 'error')
        setMode('reviewing')
        return
      }

      if (result.stdout) writeToTerminal(result.stdout, 'success')
      if (result.stderr) writeToTerminal(result.stderr, 'error')

      addExecutedStep({
        command: currentStep.command,
        output: result.stdout + result.stderr,
        exit_code: result.exit_code,
        approved: true,
        category: 'fix_step',
        timestamp: new Date().toISOString(),
      })

      // Check if all steps done
      const totalSteps = phase2Result!.hypothesis.fix_steps.length
      if (currentStepIndex + 1 >= totalSteps) {
        await handleComplete()
      } else {
        advanceStep()
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      writeToTerminal(`\x1b[31m[ERROR] ${msg}\x1b[0m\r\n`, 'error')
      setMode('reviewing')
    }
  }

  async function handleComplete() {
    if (!activeTicketId || !phase2Result) return
    setMode('completing')
    writeToTerminal('\r\n\x1b[36m[HERMITS] Running validation...\x1b[0m\r\n', 'system')

    try {
      const validation = await runValidation(activeTicketId)
      writeToTerminal(validation.output, validation.passed ? 'success' : 'warn')

      writeToTerminal('\x1b[36m[HERMITS] Closing ticket...\x1b[0m\r\n', 'system')

      const startTime = sessionStartTime ?? new Date().toISOString()
      const endTime = new Date().toISOString()
      const resolutionMinutes = Math.round(
        (new Date(endTime).getTime() - new Date(startTime).getTime()) / 60000,
      )

      const pillarAfter = phase1Result?.pillar_baseline ?? {
        service_state_output: '',
        functional_impact_output: '',
        durability_output: '',
      }

      await completeTicket({
        ticket_id: activeTicketId,
        chosen_hypothesis_index: 0,
        pillar_after_results: pillarAfter,
        executed_steps: executedSteps,
        technician_id: 'default',
        technician_notes: '',
        resolution_time_minutes: resolutionMinutes,
        command_decisions: executedSteps.map((s) => [s.command, s.approved] as [string, boolean]),
      })

      await submitActivity({
        ticket_id: activeTicketId,
        start_datetime: startTime,
        end_datetime: endTime,
        summary: phase2Result.hypothesis.hypothesis_title,
        root_cause: phase2Result.hypothesis.root_cause_explanation,
        actions_taken: executedSteps.map((s) => s.command).join('; '),
        commands_summary: executedSteps.map((s) => s.command).join('\n'),
        validation_result: validation.passed ? 'PASSED' : 'FAILED',
      })

      await updateTicketStatus(activeTicketId, 'DONE')
      qc.invalidateQueries({ queryKey: ['tickets'] })

      setMode('complete')
      writeToTerminal('\x1b[32m[HERMITS] ✓ Ticket resolved and closed.\x1b[0m\r\n', 'success')
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      writeToTerminal(`\x1b[31m[ERROR] Completion failed: ${msg}\x1b[0m\r\n`, 'error')
      setMode('reviewing')
    }
  }

  function handleManualToggle() {
    setMode(mode === 'manual' ? 'reviewing' : 'manual')
  }

  if (mode === 'idle' || mode === 'complete') return null

  return (
    <div className="flex items-center gap-2 px-4 py-3 border-t border-slate-800 bg-slate-900/80 backdrop-blur">
      {/* Accept */}
      <button
        onClick={handleAccept}
        disabled={!canAccept || !!isBlocked || (mode as string) === 'executing' || (mode as string) === 'completing'}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {(mode as string) === 'executing' || (mode as string) === 'completing' ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <CheckCircle size={14} />
        )}
        {(mode as string) === 'completing' ? 'Closing...' : (mode as string) === 'executing' ? 'Running...' : `Accept Step ${currentStepIndex + 1}`}
      </button>

      {/* Manual Fix */}
      <button
        onClick={handleManualToggle}
        disabled={!canManual}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
          mode === 'manual'
            ? 'bg-blue-600 hover:bg-blue-500 text-white'
            : 'bg-slate-700 hover:bg-slate-600 text-slate-200'
        }`}
      >
        <Terminal size={14} />
        {mode === 'manual' ? 'Exit Manual' : 'Manual Fix'}
      </button>

      {/* Abort */}
      <button
        onClick={abort}
        disabled={!canAbort}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-900/60 hover:bg-red-800 text-red-300 text-sm font-medium border border-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed ml-auto"
      >
        <XCircle size={14} />
        Abort
      </button>

      {isBlocked && (
        <span className="text-xs text-red-400 ml-2">⚠ Step blocked by safety check</span>
      )}
    </div>
  )
}
