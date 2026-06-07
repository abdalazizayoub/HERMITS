import { create } from 'zustand'
import type { Phase1Result, Phase2Result, ExecutedStep, ReconOutput } from '../types/agent'

export type WorkbenchMode =
  | 'idle'
  | 'phase1_loading'
  | 'recon_loading'
  | 'phase2_loading'
  | 'reviewing'
  | 'executing'
  | 'manual'
  | 'completing'
  | 'complete'
  | 'validated_failed'
  | 'error'

// Snapshot saved per ticket in localStorage
export interface TicketSession {
  ticketId: number
  savedAt: string
  phase1Result: Phase1Result | null
  phase2Result: Phase2Result | null
  reconOutput: ReconOutput | null
  executedSteps: ExecutedStep[]
  sessionStartTime: string | null
  validationPassed: boolean | null
  validationOutput: string | null
}

const STORAGE_KEY = 'hermits_sessions'

function loadSessions(): Record<number, TicketSession> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveSessions(sessions: Record<number, TicketSession>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch {
    // localStorage full — ignore
  }
}

interface WorkbenchState {
  activeTicketId: number | null
  phase1Result: Phase1Result | null
  phase2Result: Phase2Result | null
  reconOutput: ReconOutput | null
  currentStepIndex: number
  executedSteps: ExecutedStep[]
  sessionStartTime: string | null
  mode: WorkbenchMode
  errorMessage: string | null
  validationPassed: boolean | null
  validationOutput: string | null
  terminalRef: ((line: string, type?: 'info' | 'success' | 'error' | 'system' | 'warn') => void) | null

  // Per-ticket session cache
  ticketSessions: Record<number, TicketSession>

  // Monotonically increasing — incremented by reanalyze() so WorkbenchPanel
  // can distinguish a re-run of the same ticket from the initial run.
  reanalyzeKey: number

  // Set to true by reanalyze(); consumed (and reset) by the next Phase 1 call
  // so the backend skips the prewarm cache and generates fresh analysis.
  forceRefreshPhase1: boolean

  setActiveTicket: (id: number) => void
  setMode: (m: WorkbenchMode) => void
  setPhase1Result: (r: Phase1Result) => void
  setReconOutput: (r: ReconOutput) => void
  setPhase2Result: (r: Phase2Result) => void
  setError: (msg: string) => void
  advanceStep: () => void
  addExecutedStep: (step: ExecutedStep) => void
  setTerminalRef: (fn: (line: string, type?: 'info' | 'success' | 'error' | 'system' | 'warn') => void) => void
  writeToTerminal: (line: string, type?: 'info' | 'success' | 'error' | 'system' | 'warn') => void
  abort: () => void
  reset: () => void

  // Session management
  saveSession: (validationPassed: boolean, validationOutput: string) => void
  reanalyze: () => void
  clearSession: (ticketId: number) => void
  getSession: (ticketId: number) => TicketSession | null
  enterManualMode: () => void
  consumeForceRefresh: () => boolean
}

export const useWorkbenchStore = create<WorkbenchState>((set, get) => ({
  activeTicketId: null,
  phase1Result: null,
  phase2Result: null,
  reconOutput: null,
  currentStepIndex: 0,
  executedSteps: [],
  sessionStartTime: null,
  mode: 'idle',
  errorMessage: null,
  validationPassed: null,
  validationOutput: null,
  terminalRef: null,
  ticketSessions: loadSessions(),
  reanalyzeKey: 0,
  forceRefreshPhase1: false,

  setActiveTicket: (id) => {
    const sessions = loadSessions()
    const saved = sessions[id]

    if (saved) {
      // Restore previously completed/run session — skip the pipeline
      set({
        activeTicketId: id,
        phase1Result: saved.phase1Result,
        phase2Result: saved.phase2Result,
        reconOutput: saved.reconOutput,
        executedSteps: saved.executedSteps,
        sessionStartTime: saved.sessionStartTime,
        validationPassed: saved.validationPassed,
        validationOutput: saved.validationOutput,
        currentStepIndex: saved.executedSteps.filter((s) => s.category === 'fix_step').length,
        mode: saved.validationPassed === true
          ? 'complete'
          : saved.validationPassed === false
          ? 'validated_failed'
          : 'reviewing',
        errorMessage: null,
      })
    } else {
      // Fresh ticket — start the pipeline
      set({
        activeTicketId: id,
        phase1Result: null,
        phase2Result: null,
        reconOutput: null,
        currentStepIndex: 0,
        executedSteps: [],
        sessionStartTime: new Date().toISOString(),
        mode: 'phase1_loading',
        errorMessage: null,
        validationPassed: null,
        validationOutput: null,
      })
    }
  },

  setMode: (m) => set({ mode: m }),
  setPhase1Result: (r) => set({ phase1Result: r }),
  setReconOutput: (r) => set({ reconOutput: r }),
  setPhase2Result: (r) => set({ phase2Result: r, currentStepIndex: 0 }),
  setError: (msg) => set({ mode: 'error', errorMessage: msg }),

  advanceStep: () => {
    const { currentStepIndex, phase2Result } = get()
    const totalSteps = phase2Result?.hypothesis?.fix_steps?.length ?? 0
    if (currentStepIndex + 1 >= totalSteps) {
      set({ mode: 'completing' })
    } else {
      set({ currentStepIndex: currentStepIndex + 1, mode: 'reviewing' })
    }
  },

  addExecutedStep: (step) =>
    set((state) => ({ executedSteps: [...state.executedSteps, step] })),

  setTerminalRef: (fn) => set({ terminalRef: fn }),

  writeToTerminal: (line, type) => {
    const { terminalRef } = get()
    terminalRef?.(line, type)
  },

  enterManualMode: () => {
    const { mode, writeToTerminal } = get()
    if (mode === 'idle' || mode === 'complete' || mode === 'completing') return
    writeToTerminal('\r\n\x1b[36m[HERMITS] Entering manual shell mode...\x1b[0m\r\n', 'system')
    set({ mode: 'manual' })
  },

  consumeForceRefresh: () => {
    const { forceRefreshPhase1 } = get()
    if (forceRefreshPhase1) {
      set({ forceRefreshPhase1: false })
      return true
    }
    return false
  },

  saveSession: (validationPassed, validationOutput) => {
    const { activeTicketId, phase1Result, phase2Result, reconOutput, executedSteps, sessionStartTime } = get()
    if (!activeTicketId) return

    const session: TicketSession = {
      ticketId: activeTicketId,
      savedAt: new Date().toISOString(),
      phase1Result,
      phase2Result,
      reconOutput,
      executedSteps,
      sessionStartTime,
      validationPassed,
      validationOutput,
    }

    const sessions = { ...loadSessions(), [activeTicketId]: session }
    saveSessions(sessions)
    set({ ticketSessions: sessions, validationPassed, validationOutput })
  },

  reanalyze: () => {
    const { activeTicketId } = get()
    if (!activeTicketId) return

    // Clear saved session for this ticket
    const sessions = loadSessions()
    delete sessions[activeTicketId]
    saveSessions(sessions)

    set((state) => ({
      phase1Result: null,
      phase2Result: null,
      reconOutput: null,
      currentStepIndex: 0,
      executedSteps: [],
      sessionStartTime: new Date().toISOString(),
      mode: 'phase1_loading',
      errorMessage: null,
      validationPassed: null,
      validationOutput: null,
      ticketSessions: sessions,
      reanalyzeKey: state.reanalyzeKey + 1,
      forceRefreshPhase1: true,
    }))
  },

  clearSession: (ticketId) => {
    const sessions = loadSessions()
    delete sessions[ticketId]
    saveSessions(sessions)
    set({ ticketSessions: sessions })
  },

  getSession: (ticketId) => {
    const sessions = loadSessions()
    return sessions[ticketId] ?? null
  },

  abort: () => {
    const { terminalRef } = get()
    terminalRef?.('\r\n\x1b[33m[ABORTED] Session reset\x1b[0m\r\n', 'warn')
    set({
      mode: 'idle',
      phase1Result: null,
      phase2Result: null,
      reconOutput: null,
      currentStepIndex: 0,
      executedSteps: [],
      errorMessage: null,
      validationPassed: null,
      validationOutput: null,
    })
  },

  reset: () =>
    set({
      activeTicketId: null,
      phase1Result: null,
      phase2Result: null,
      reconOutput: null,
      currentStepIndex: 0,
      executedSteps: [],
      sessionStartTime: null,
      mode: 'idle',
      errorMessage: null,
      validationPassed: null,
      validationOutput: null,
    }),
}))
