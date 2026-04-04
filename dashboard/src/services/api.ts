import type {
  AgentSummary, Conflict, ConflictHotspot, ConflictSummary,
  CostSummary, Decision, DecisionList, DriftResult, HealthStatus,
  LatencyStats, OverviewSummary, TimelinePoint,
} from '../types'

// ── API base URL ───────────────────────────────────────────────────────────
// In dev: Vite proxy handles /api → http://localhost:8000
// In production: __API_URL__ is injected by vite.config.ts from VITE_API_URL.
//   If empty string (''), calls go to same origin (works behind nginx proxy).
//   If set (e.g. 'http://myserver:8000'), calls go directly to that host.
declare const __API_URL__: string

const _apiBase = (() => {
  try {
    // __API_URL__ is injected at build time; may be undefined in dev
    return typeof __API_URL__ !== 'undefined' && __API_URL__ !== ''
      ? __API_URL__
      : ''
  } catch {
    return ''
  }
})()

const BASE = `${_apiBase}/api`
const HEALTH_BASE = `${_apiBase}`

// ── Generic fetch helper ───────────────────────────────────────────────────
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

async function getRoot<T>(path: string): Promise<T> {
  const url = new URL(`${HEALTH_BASE}${path}`, window.location.origin)
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<T>
}

// ── API surface ────────────────────────────────────────────────────────────
export const api = {
  // Health
  health: () => getRoot<HealthStatus>('/health'),

  // Overview
  overviewSummary: (hours = 24) => get<OverviewSummary>('/metrics/summary', { hours }),

  // Decisions
  decisions: (params?: {
    agent_id?: string
    session_id?: string   // AFMX: session_id = execution_id — groups all nodes of one run
    decision_type?: string
    limit?: number
    offset?: number
  }) => get<DecisionList>('/decisions', params as Record<string, string | number | undefined>),
  decision:          (id: string) => get<Decision>(`/decisions/${id}`),
  decisionReasoning: (id: string) => get<Record<string, unknown>>(`/decisions/${id}/reasoning`),

  // AFMX Sessions — convenience wrapper: filter decisions by AFMX execution_id
  afmxSession: (executionId: string, limit = 50) =>
    get<DecisionList>('/decisions', { session_id: executionId, limit }),

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
