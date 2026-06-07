import client from './client'
import type { Phase1Result, Phase2Result, PillarResult, ExecutedStep } from '../types/agent'

// SSE-based Phase 1
export async function startPhase1(
  ticketId: number,
  technicianId = 'default',
  forceRefresh = false,
): Promise<{ job_id: string }> {
  const res = await client.post('/api/agent/ai/phase1/start', {
    ticket_id: ticketId,
    technician_id: technicianId,
    force_refresh: forceRefresh,
  })
  return res.data
}

export function streamPhase1Status(jobId: string): EventSource {
  return new EventSource(`/api/agent/ai/phase1/status/${jobId}`)
}

// SSE-based Phase 2
export async function startPhase2(
  ticketId: number,
  reconOutput: Record<string, string | undefined>,
  pillarBaseline: PillarResult | null,
  technicianId = 'default',
): Promise<{ job_id: string }> {
  const res = await client.post('/api/agent/ai/phase2/start', {
    ticket_id: ticketId,
    technician_id: technicianId,
    recon_output: reconOutput,
    pillar_baseline: pillarBaseline,
  })
  return res.data
}

export function streamPhase2Status(jobId: string): EventSource {
  return new EventSource(`/api/agent/ai/phase2/status/${jobId}`)
}

// Fallback: direct POST (non-streaming)
export async function runPhase1Direct(
  ticketId: number,
  technicianId = 'default',
  forceRefresh = false,
): Promise<Phase1Result> {
  const res = await client.post('/api/agent/ai/phase1', {
    ticket_id: ticketId,
    technician_id: technicianId,
    force_refresh: forceRefresh,
  })
  return res.data
}

export async function runPhase2Direct(
  ticketId: number,
  reconOutput: Record<string, string | undefined>,
  pillarBaseline: PillarResult | null,
  technicianId = 'default',
): Promise<Phase2Result> {
  const res = await client.post('/api/agent/ai/phase2', {
    ticket_id: ticketId,
    technician_id: technicianId,
    recon_output: reconOutput,
    pillar_baseline: pillarBaseline,
  })
  return res.data
}

export interface CompleteRequest {
  ticket_id: number
  chosen_hypothesis_index: number
  pillar_after_results: PillarResult
  executed_steps: ExecutedStep[]
  technician_id: string
  technician_notes: string
  resolution_time_minutes: number
  command_decisions: [string, boolean][]
}

export async function completeTicket(req: CompleteRequest) {
  const res = await client.post('/api/agent/ai/complete', req)
  return res.data
}
