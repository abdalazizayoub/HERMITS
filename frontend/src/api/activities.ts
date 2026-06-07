import client from './client'

export interface ActivityPayload {
  ticket_id: number
  start_datetime: string
  end_datetime: string
  summary: string
  root_cause: string
  actions_taken: string
  commands_summary: string
  validation_result: string
}

export async function submitActivity(payload: ActivityPayload): Promise<{ activity_id: string }> {
  const res = await client.post('/api/activities/submit', payload)
  return res.data
}

export async function resetEnvironment(): Promise<{ ok: boolean; detail: unknown }> {
  const res = await client.post('/api/activities/reset')
  return res.data
}
