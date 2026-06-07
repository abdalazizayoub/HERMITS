export interface MonthlyDigestResult {
  transcript: string
  total_tickets: number
  avg_resolution_minutes: number
  most_common_root_cause: string
  top_incidents: string[]
}
