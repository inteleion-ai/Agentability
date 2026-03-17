/* ── API Types — mirrors platform/api/schemas.py exactly ── */

export interface PageMeta {
  total: number
  limit: number
  offset: number
}

export interface Decision {
  decision_id: string
  agent_id: string
  session_id: string | null
  timestamp: string
  latency_ms: number | null
  decision_type: string
  confidence: number | null
  quality_score: number | null
  llm_calls: number
  total_tokens: number
  total_cost_usd: number
  reasoning: string[]
  uncertainties: string[]
  assumptions: string[]
  constraints_checked: string[]
  constraints_violated: string[]
  data_sources: string[]
  tags: string[]
  output_data: Record<string, unknown>
  metadata: Record<string, unknown>
}

export interface DecisionList {
  items: Decision[]
  meta: PageMeta
}

export interface AgentSummary {
  agent_id: string
  total_decisions: number
  avg_confidence: number | null
  avg_latency_ms: number | null
  success_rate: number | null
  total_cost_usd: number
  total_tokens: number
  total_llm_calls: number
}

export interface DriftResult {
  drift_detected: boolean
  severity: string
  agent_id: string
  current_confidence?: number
  baseline_confidence?: number
  drift_magnitude?: number
  current_stddev?: number
  baseline_stddev?: number
  recent_samples?: number
  baseline_samples?: number
  recommendation?: string
  timeline?: TimelinePoint[]
  error?: string
}

export interface TimelinePoint {
  timestamp: string
  avg_confidence?: number
  min_confidence?: number
  max_confidence?: number
  avg_latency_ms?: number
  p95_latency_ms?: number
  cost_usd?: number
  count?: number
  sample_count?: number
}

export interface CostSummary {
  total_cost_usd: number
  total_tokens: number
  total_calls: number
  by_model: Record<string, number>
  by_provider: Record<string, number>
  cost_per_decision: number
}

export interface Conflict {
  conflict_id: string
  session_id: string
  timestamp: string
  conflict_type: string
  involved_agents: string[]
  severity: number
  resolved: boolean
  resolution_strategy: string | null
  resolution_outcome: string | null
  resolution_time_ms: number | null
}

export interface ConflictHotspot {
  agents: string[]
  conflict_count: number
  avg_severity: number
  win_rates: Record<string, number>
}

export interface ConflictSummary {
  total: number
  resolved: number
  unresolved: number
  avg_severity: number
  by_type: Record<string, number>
}

export interface OverviewSummary {
  total_decisions: number
  unique_agents: number
  avg_confidence: number | null
  avg_latency_ms: number | null
  violation_rate: number
  total_cost_usd: number
  total_tokens: number
  window_hours: number
}

export interface LatencyStats {
  p50: number
  p95: number
  p99: number
  avg: number
  count: number
}

export interface HealthStatus {
  status: string
  version: string
  db_path: string
  total_decisions: number
  total_conflicts: number
  uptime_seconds: number
}
