import client from './client'
import type { MonthlyDigestResult } from '../types/digest'

export async function getDigestMeta(month: string): Promise<MonthlyDigestResult> {
  const res = await client.post('/api/agent/ai/voice/digest', { month })
  return res.data
}

export async function getDigestAudio(month: string): Promise<string> {
  const res = await client.post('/api/agent/ai/voice/digest/audio', { month }, { responseType: 'blob' })
  return URL.createObjectURL(res.data)
}

export async function getTicketVoiceSummary(ticketId: number): Promise<string> {
  const res = await client.get(`/api/agent/ai/voice/summary/${ticketId}`, { responseType: 'blob' })
  return URL.createObjectURL(res.data)
}
