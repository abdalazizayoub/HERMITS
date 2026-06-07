import type { KBMatch } from './kb'

export type RiskLevel = 'low' | 'medium' | 'high'

export interface FixStep {
  command: string
  rationale: string
  risk_level: RiskLevel
}

export interface SafetyResult {
  is_safe: boolean
  reason: string | null
  warnings: string[]
}

export interface PillarSpec {
  service_state_cmd: string
  functional_impact_cmd: string
  durability_cmd: string
  definition_of_done: string
}

export interface PillarResult {
  service_state_output: string
  functional_impact_output: string
  durability_output: string
}

export interface Hypothesis {
  hypothesis_title: string
  root_cause_explanation: string
  evidence: string[]
  fix_steps: FixStep[]
  expected_pillar_outcomes: Record<string, string>
  confidence_rationale: string
}

export interface Phase1Result {
  pillar_spec: PillarSpec
  kb_matches: KBMatch[]
  memory_context: string
  cache_hit: boolean
  pillar_baseline: PillarResult | null
}

export interface Phase2Result {
  hypothesis: Hypothesis
  safety_results: SafetyResult[]
  pillar_spec: PillarSpec
  recon_summary: string
  all_hypotheses: Hypothesis[]
}

export interface ExecutedStep {
  command: string
  output: string
  exit_code: number
  approved: boolean
  category: 'fix_step' | 'manual'
  timestamp: string
}

export interface ReconOutput {
  logs?: string
  service_statuses?: string
  disk_usage?: string
  config_files?: string
  port_config?: string
  network?: string
  database?: string
  [key: string]: string | undefined
}
