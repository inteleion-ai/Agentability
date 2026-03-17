import type {
  AgentSummary, Conflict, ConflictHotspot, ConflictSummary,
  CostSummary, Decision, DecisionList, DriftResult, HealthStatus,
  LatencyStats, OverviewSummary, TimelinePoint,
} from '../types'

const BASE = '/api'

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    })
  }
  const res = await fetch(url.toString())
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  // Health
  health: () => get<HealthStatus>('/health'),

  // Overview
  overviewSummary: (hours = 24) => get<OverviewSummary>('/metrics/summary', { hours }),

  // Decisions
  decisions: (params?: {
    agent_id?: string; session_id?: string; decision_type?: string
    limit?: number; offset?: number
  }) => get<DecisionList>('/decisions', params as Record<string, string | number | undefined>),
  decision: (id: string) => get<Decision>(`/decisions/${id}`),
  decisionReasoning: (id: string) => get<Record<string, unknown>>(`/decisions/${id}/reasoning`),

  // Agents
  agents: (limit = 50) => get<AgentSummary[]>('/agents', { limit }),
  agentSummary: (agentId: string, hours = 24) =>
    get<AgentSummary>(`/agents/${agentId}/summary`, { hours }),
  agentDrift: (agentId: string, windowHours = 24, baselineDays = 7) =>
    get<DriftResult>(`/agents/${agentId}/drift`, { window_hours: windowHours, baseline_days: baselineDays }),
  agentConfidenceTimeline: (agentId: string, hours = 24, bucketMinutes = 60) =>
    get<TimelinePoint[]>(`/agents/${agentId}/confidence-timeline`, { hours, bucket_minutes: bucketMinutes }),

  // Metrics / Cost
  costSummary: (hours = 24) => get<CostSummary>('/metrics/cost', { hours }),
  costTimeline: (hours = 24, bucketMinutes = 60) =>
    get<TimelinePoint[]>('/metrics/cost/timeline', { hours, bucket_minutes: bucketMinutes }),
  latencyStats: (agentId?: string, hours = 24) =>
    get<LatencyStats>('/metrics/latency', { agent_id: agentId, hours }),
  latencyTimeline: (agentId?: string, hours = 24, bucketMinutes = 60) =>
    get<TimelinePoint[]>('/metrics/latency/timeline', { agent_id: agentId, hours, bucket_minutes: bucketMinutes }),

  // Conflicts
  conflicts: (params?: { hours?: number; min_severity?: number; limit?: number }) =>
    get<Conflict[]>('/conflicts', params as Record<string, string | number | undefined>),
  conflictHotspots: (hours = 168) => get<ConflictHotspot[]>('/conflicts/hotspots', { hours }),
  conflictTimeline: (hours = 24, bucketMinutes = 60) =>
    get<TimelinePoint[]>('/conflicts/timeline', { hours, bucket_minutes: bucketMinutes }),
  conflictSummary: (hours = 24) => get<ConflictSummary>('/conflicts/summary', { hours }),
}
