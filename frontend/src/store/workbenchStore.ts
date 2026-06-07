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
  | 'error'

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
  terminalRef: ((line: string, type?: 'info' | 'success' | 'error' | 'system' | 'warn') => void) | null

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
  terminalRef: null,

  setActiveTicket: (id) =>
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
    }),

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
    }),
}))
