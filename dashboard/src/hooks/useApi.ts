import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { api } from '../services/api'

// ── Query keys ────────────────────────────────────────────────────────────
export const QK = {
  health:               ['health'],
  overview:    (h: number)                    => ['overview', h],
  decisions:   (p: object)                    => ['decisions', p],
  decision:    (id: string)                   => ['decision', id],
  afmxSession: (execId: string)               => ['afmxSession', execId],
  agents:                                        ['agents'],
  agentSummary:(id: string, h: number)        => ['agentSummary', id, h],
  agentDrift:  (id: string)                   => ['agentDrift', id],
  agentTimeline:(id: string, h: number)       => ['agentTimeline', id, h],
  cost:        (h: number)                    => ['cost', h],
  costTimeline:(h: number)                    => ['costTimeline', h],
  latency:     (id: string | undefined, h: number) => ['latency', id, h],
  latencyTimeline: (id: string | undefined, h: number) => ['latencyTimeline', id, h],
  conflicts:   (p: object)                    => ['conflicts', p],
  conflictHotspots: (h: number)               => ['conflictHotspots', h],
  conflictTimeline: (h: number)               => ['conflictTimeline', h],
  conflictSummary:  (h: number)               => ['conflictSummary', h],
} as const

const STALE = 30_000   // 30 s — data considered fresh
const POLL  = 60_000   // 1 min background refetch

function q<T>(
  key: readonly unknown[],
  fn: () => Promise<T>,
  opts?: Partial<UseQueryOptions<T>>
) {
  return useQuery<T>({ queryKey: key, queryFn: fn, staleTime: STALE, refetchInterval: POLL, ...opts })
}

// ── Hooks ─────────────────────────────────────────────────────────────────
export const useHealth = () =>
  q(QK.health, api.health)

export const useOverview = (hours = 24) =>
  q(QK.overview(hours), () => api.overviewSummary(hours))

export const useDecisions = (params?: Parameters<typeof api.decisions>[0]) =>
  q(QK.decisions(params ?? {}), () => api.decisions(params))

export const useDecision = (id: string) =>
  q(QK.decision(id), () => api.decision(id), { enabled: !!id })

/** Filter decisions by AFMX execution_id (session_id = afmx execution_id) */
export const useAfmxSession = (executionId: string) =>
  q(QK.afmxSession(executionId), () => api.afmxSession(executionId), { enabled: !!executionId })

export const useAgents = () =>
  q(QK.agents, () => api.agents())

export const useAgentSummary = (agentId: string, hours = 24) =>
  q(QK.agentSummary(agentId, hours), () => api.agentSummary(agentId, hours), { enabled: !!agentId })

export const useAgentDrift = (agentId: string) =>
  q(QK.agentDrift(agentId), () => api.agentDrift(agentId), { enabled: !!agentId })

export const useAgentTimeline = (agentId: string, hours = 24) =>
  q(QK.agentTimeline(agentId, hours), () => api.agentConfidenceTimeline(agentId, hours), { enabled: !!agentId })

export const useCost = (hours = 24) =>
  q(QK.cost(hours), () => api.costSummary(hours))

export const useCostTimeline = (hours = 24) =>
  q(QK.costTimeline(hours), () => api.costTimeline(hours))

export const useLatency = (agentId?: string, hours = 24) =>
  q(QK.latency(agentId, hours), () => api.latencyStats(agentId, hours))

export const useLatencyTimeline = (agentId?: string, hours = 24) =>
  q(QK.latencyTimeline(agentId, hours), () => api.latencyTimeline(agentId, hours))

export const useConflicts = (params?: Parameters<typeof api.conflicts>[0]) =>
  q(QK.conflicts(params ?? {}), () => api.conflicts(params))

export const useConflictHotspots = (hours = 168) =>
  q(QK.conflictHotspots(hours), () => api.conflictHotspots(hours))

export const useConflictTimeline = (hours = 24) =>
  q(QK.conflictTimeline(hours), () => api.conflictTimeline(hours))

export const useConflictSummary = (hours = 24) =>
  q(QK.conflictSummary(hours), () => api.conflictSummary(hours))
