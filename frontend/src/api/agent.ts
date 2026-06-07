import client from './client'
import type { ReconOutput } from '../types/agent'

export interface ExecuteRequest {
  ticket_id: number
  command: string
  category?: string
}

export interface ExecuteResult {
  stdout: string
  stderr: string
  exit_code: number
  blocked: boolean
  reason?: string
  warnings?: string[]
}

export async function runRecon(ticketId: number): Promise<ReconOutput> {
  const res = await client.post('/api/agent/recon', { ticket_id: ticketId })
  return res.data
}

export async function executeCommand(req: ExecuteRequest): Promise<ExecuteResult> {
  const res = await client.post('/api/agent/execute', req)
  return res.data
}

export async function runValidation(ticketId: number): Promise<{ output: string; passed: boolean }> {
  const res = await client.post('/api/agent/validate', { ticket_id: ticketId })
  return res.data
}

export async function getAuditLog(ticketId: number): Promise<unknown[]> {
  const res = await client.get(`/api/agent/audit/${ticketId}`)
  return res.data
}
