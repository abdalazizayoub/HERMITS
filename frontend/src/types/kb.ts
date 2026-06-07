export interface KBMatch {
  entry_id: string
  similarity_score: number
  confidence_boost: number
  root_cause: string
  fix_commands: string[]
  resolution_time_minutes: number
  service_hint: string | null
  validation_passed: boolean
}
