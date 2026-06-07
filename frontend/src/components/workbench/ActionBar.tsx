import { useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle, XCircle, Terminal, Loader2, SkipForward, ShieldAlert,
  RefreshCw, FlaskConical, CheckCircle2, AlertCircle,
} from 'lucide-react'
import { useWorkbenchStore } from '../../store/workbenchStore'
import { executeCommand, runValidation } from '../../api/agent'
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
    validationPassed,
    setMode,
    advanceStep,
    addExecutedStep,
    writeToTerminal,
    abort,
    saveSession,
    reanalyze,
    enterManualMode,
  } = useWorkbenchStore()

  const canAccept = mode === 'reviewing' && phase2Result !== null
  const canAbort = ['phase1_loading', 'recon_loading', 'phase2_loading', 'reviewing', 'executing', 'manual'].includes(mode)
  const canSkip = mode === 'reviewing' && phase2Result !== null
  const isRunning = mode === 'executing' || mode === 'completing'
  const hasManualSteps = executedSteps.filter((s) => s.category === 'manual').length > 0
  const canManualSubmit = mode === 'manual' && (executedSteps.length > 0)
  // Allow entering manual shell from any active non-terminal state
  const canEnterManual = ['reviewing', 'manual', 'phase1_loading', 'recon_loading', 'phase2_loading'].includes(mode)

  const currentStep = phase2Result?.hypothesis.fix_steps[currentStepIndex]
  const safety = phase2Result?.safety_results[currentStepIndex]
  const isBlocked = safety && !safety.is_safe
  const totalSteps = phase2Result?.hypothesis.fix_steps.length ?? 0

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
        writeToTerminal(`\x1b[31m[BLOCKED] ${result.reason ?? 'Command blocked by safety layer'}\x1b[0m\r\n`, 'error')
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

  function handleSkip() {
    if (!currentStep) return
    writeToTerminal(`\x1b[33m[SKIPPED] ${currentStep.command}\x1b[0m\r\n`, 'warn')
    addExecutedStep({
      command: currentStep.command,
      output: '[skipped by technician]',
      exit_code: -1,
      approved: false,
      category: 'fix_step',
      timestamp: new Date().toISOString(),
    })
    if (currentStepIndex + 1 >= totalSteps) {
      handleComplete()
    } else {
      advanceStep()
    }
  }

  async function handleComplete(fromManual = false) {
    if (!activeTicketId) return
    if (!phase2Result && !fromManual) return

    setMode('completing')
    writeToTerminal('\r\n\x1b[36m[HERMITS] Running validation script...\x1b[0m\r\n', 'system')

    try {
      const validation = await runValidation(activeTicketId)
      writeToTerminal(validation.output, validation.passed ? 'success' : 'warn')

      const startTime = sessionStartTime ?? new Date().toISOString()
      const endTime = new Date().toISOString()
      const resolutionMinutes = Math.round(
        (new Date(endTime).getTime() - new Date(startTime).getTime()) / 60000,
      )

      // Build activity fields — handle manual-only flow (no AI hypothesis)
      const summary = phase2Result?.hypothesis.hypothesis_title
        ?? `Manual fix: ${executedSteps.length} command${executedSteps.length !== 1 ? 's' : ''} executed`
      const rootCause = phase2Result?.hypothesis.root_cause_explanation
        ?? 'Manually diagnosed and resolved by technician'
      const approvedSteps = executedSteps.filter((s) => s.approved && s.exit_code !== -1)

      writeToTerminal('\x1b[36m[HERMITS] Submitting activity to ERP...\x1b[0m\r\n', 'system')

      const pillarAfter = phase1Result?.pillar_baseline ?? {
        service_state_output: '',
        functional_impact_output: '',
        durability_output: '',
      }

      // Only call AI complete if we have phase2 results
      if (phase2Result) {
        await completeTicket({
          ticket_id: activeTicketId,
          chosen_hypothesis_index: 0,
          pillar_after_results: pillarAfter,
          executed_steps: executedSteps,
          technician_id: 'default',
          technician_notes: hasManualSteps ? 'Technician performed additional manual fixes.' : '',
          resolution_time_minutes: resolutionMinutes,
          command_decisions: executedSteps.map((s) => [s.command, s.approved] as [string, boolean]),
        })
      }

      await submitActivity({
        ticket_id: activeTicketId,
        start_datetime: startTime,
        end_datetime: endTime,
        summary,
        root_cause: rootCause,
        actions_taken: executedSteps.map((s) =>
          `${s.approved ? '✓' : s.exit_code === -1 ? '↩' : '✗'} ${s.command}`,
        ).join('\n'),
        commands_summary: approvedSteps.map((s) => s.command).join('\n'),
        validation_result: validation.passed ? 'PASSED' : 'FAILED',
      })

      // Save session regardless of validation outcome
      saveSession(validation.passed, validation.output)

      if (validation.passed) {
        // Only mark DONE in ERP when validation passed
        await updateTicketStatus(activeTicketId, 'DONE')
        qc.invalidateQueries({ queryKey: ['tickets'] })
        setMode('complete')
        writeToTerminal('\x1b[32m[HERMITS] ✓ Validation PASSED — ticket closed.\x1b[0m\r\n', 'success')
      } else {
        // Validation failed — keep OPEN, allow technician to retry
        qc.invalidateQueries({ queryKey: ['tickets'] })
        setMode('validated_failed')
        writeToTerminal('\x1b[33m[HERMITS] ✗ Validation FAILED — ticket remains open. You can retry manually.\x1b[0m\r\n', 'warn')
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      writeToTerminal(`\x1b[31m[ERROR] Completion failed: ${msg}\x1b[0m\r\n`, 'error')
      setMode('reviewing')
    }
  }

  // Completed or failed — show re-analyze / manual retry bar
  if (mode === 'complete' || mode === 'validated_failed') {
    return (
      <div
        className="flex items-center gap-2 px-4 py-2.5 border-t glass"
        style={{ borderTopColor: mode === 'complete' ? 'rgba(52,211,153,0.2)' : 'rgba(251,191,36,0.2)' }}
      >
        <div className="flex items-center gap-1.5 mr-2">
          {mode === 'complete' ? (
            <CheckCircle2 size={14} className="text-emerald-400" />
          ) : (
            <AlertCircle size={14} className="text-amber-400" />
          )}
          <span className={`text-xs font-bold ${mode === 'complete' ? 'text-emerald-400' : 'text-amber-400'}`}>
            {mode === 'complete' ? 'Validation PASSED' : 'Validation FAILED'}
          </span>
        </div>

        {mode === 'validated_failed' && (
          <button
            onClick={() => setMode('manual')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 text-xs font-medium border border-cyan-500/40 hover:bg-cyan-500/30 hover:shadow-glow-cyan transition-all"
          >
            <Terminal size={12} />
            Retry with Manual Shell
          </button>
        )}

        <button
          onClick={reanalyze}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-500/15 text-purple-400 text-xs font-medium border border-purple-500/30 hover:bg-purple-500/25 transition-all"
        >
          <RefreshCw size={12} />
          Re-analyze
        </button>
      </div>
    )
  }

  if (mode === 'idle') return null

  return (
    <div
      className="flex items-center gap-2 px-4 py-2.5 border-t glass"
      style={{ borderTopColor: 'rgba(34,211,238,0.15)' }}
    >
      {/* Step progress indicator */}
      {phase2Result && !['phase1_loading', 'recon_loading', 'phase2_loading'].includes(mode) && mode !== 'manual' && (
        <span className="text-xs font-mono text-slate-600 shrink-0">
          {Math.min(currentStepIndex + 1, totalSteps)}/{totalSteps}
        </span>
      )}

      {/* In manual mode: show validate & submit prominently */}
      {mode === 'manual' && (
        <>
          {canManualSubmit && (
            <button
              onClick={() => handleComplete(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 hover:text-emerald-300 text-xs font-bold transition-all border border-emerald-500/40 hover:border-emerald-500/60 hover:shadow-glow-green"
            >
              <FlaskConical size={13} />
              Validate &amp; Submit ({executedSteps.length} cmd{executedSteps.length !== 1 ? 's' : ''})
            </button>
          )}
          <button
            onClick={() => setMode(phase2Result ? 'reviewing' : 'idle')}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 text-xs font-medium transition-all hover:shadow-glow-cyan"
          >
            <XCircle size={12} />
            Exit Shell
          </button>
          <span className="text-xs font-mono text-cyan-400 pipeline-active ml-1">● shell active</span>
        </>
      )}

      {/* Standard AI-guided flow */}
      {mode !== 'manual' && (
        <>
          <button
            onClick={handleAccept}
            disabled={!canAccept || !!isBlocked || isRunning}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 hover:text-emerald-300 text-xs font-bold transition-all disabled:opacity-30 disabled:cursor-not-allowed border border-emerald-500/40 hover:border-emerald-500/60 hover:shadow-glow-green"
          >
            {isRunning ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle size={13} />}
            {mode === 'completing' ? 'Closing...' : mode === 'executing' ? 'Running...' : `Accept Step ${currentStepIndex + 1}`}
          </button>

          <button
            onClick={handleSkip}
            disabled={!canSkip || isRunning}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 hover:text-amber-400 text-xs font-medium transition-all disabled:opacity-30 disabled:cursor-not-allowed border border-amber-500/20 hover:border-amber-500/40"
          >
            <SkipForward size={12} />
            Skip
          </button>

          {isBlocked && (
            <span className="flex items-center gap-1 text-xs text-red-400">
              <ShieldAlert size={11} />
              Safety blocked
            </span>
          )}
        </>
      )}

      {/* Manual shell toggle — available from any active state */}
      {mode !== 'manual' && canEnterManual && !isRunning && (
        <button
          onClick={enterManualMode}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/60 text-slate-500 hover:text-cyan-400 hover:bg-cyan-950/30 hover:border-cyan-500/30 text-xs font-medium transition-all border border-slate-700/60"
        >
          <Terminal size={12} />
          Manual Shell
        </button>
      )}

      {/* Abort */}
      <button
        onClick={abort}
        disabled={!canAbort}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-500 hover:text-red-400 text-xs font-medium border border-red-500/20 hover:border-red-500/40 transition-all disabled:opacity-30 disabled:cursor-not-allowed ml-auto"
      >
        <XCircle size={12} />
        Abort
      </button>
    </div>
  )
}
