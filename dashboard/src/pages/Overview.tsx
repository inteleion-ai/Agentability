import { Card, StatCard, SectionHeader, Skeleton, ErrorState, EmptyState } from '../components/ui/Card'
import {
  ConfidenceChart,
  LatencyChart,
  CostChart,
  ConflictChart,
} from '../components/charts/Charts'
import {
  useOverview,
  useAgents,
  useAgentTimeline,
  useLatencyTimeline,
  useCostTimeline,
  useConflictTimeline,
} from '../hooks/useApi'
import {
  fmtConfidence,
  fmtLatency,
  fmtCost,
  fmtTokens,
  fmtPercent,
  fmtNumber,
  confidenceColor,
} from '../utils/format'

interface OverviewProps {
  timeWindow: number
}

export default function Overview({ timeWindow }: OverviewProps) {
  const { data: overview, isLoading, error } = useOverview(timeWindow)
  const { data: agents } = useAgents()
  const firstAgent = agents?.[0]?.agent_id ?? ''
  const { data: confTl  } = useAgentTimeline(firstAgent, timeWindow)
  const { data: latTl   } = useLatencyTimeline(undefined, timeWindow)
  const { data: costTl  } = useCostTimeline(timeWindow)
  const { data: conflTl } = useConflictTimeline(timeWindow)

  if (error) return <ErrorState message="Failed to load overview — is the API running on :8000?" />

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* ── KPI cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{ height: 108, background: 'var(--bg-surface)', borderRadius: 12, border: '1px solid var(--border)' }}>
                <div style={{ padding: 16 }}>
                  <Skeleton w="55%" h={11} />
                  <div style={{ marginTop: 12 }}><Skeleton w="70%" h={28} /></div>
                  <div style={{ marginTop: 8 }}><Skeleton w="40%" h={11} /></div>
                </div>
              </div>
            ))
          : (
            <>
              <StatCard
                label="Total Decisions"
                value={fmtNumber(overview?.total_decisions ?? 0)}
                sub={`last ${timeWindow}h`}
                color="var(--blue)"
                icon={<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M2 4.5h14M2 9h9M2 13.5h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>}
              />
              <StatCard
                label="Avg Confidence"
                value={fmtConfidence(overview?.avg_confidence)}
                color={confidenceColor(overview?.avg_confidence)}
                sub="across all agents"
                icon={<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.5"/><path d="M9 5v4l3 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>}
              />
              <StatCard
                label="Avg Latency"
                value={fmtLatency(overview?.avg_latency_ms)}
                color="var(--amber)"
                sub="p50 decision time"
                icon={<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M3 9h12M12 5l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>}
              />
              <StatCard
                label="Total Cost"
                value={fmtCost(overview?.total_cost_usd)}
                color="var(--green)"
                sub={`${fmtTokens(overview?.total_tokens ?? 0)} tokens`}
                icon={<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.5"/><path d="M9 5v1m0 6v1M6.5 7.5a2 2 0 0 1 2-2h1a1.5 1.5 0 0 1 0 3H8a1.5 1.5 0 0 0 0 3h1a2 2 0 0 0 2-1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>}
              />
              <StatCard
                label="Violation Rate"
                value={fmtPercent(overview?.violation_rate ?? 0)}
                color={(overview?.violation_rate ?? 0) > 0.05 ? 'var(--red)' : 'var(--green)'}
                sub={`${overview?.unique_agents ?? 0} agents active`}
                icon={<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 1.5L16.5 15H1.5L9 1.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><path d="M9 7v4M9 13v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>}
              />
            </>
          )}
      </div>

      {/* ── Charts row 1 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Card>
          <SectionHeader
            title="Confidence Trend"
            sub={firstAgent ? `agent: ${firstAgent}` : 'no agent data — record decisions first'}
          />
          {confTl?.length
            ? <ConfidenceChart data={confTl} />
            : <EmptyState message="No confidence data yet" />
          }
        </Card>
        <Card>
          <SectionHeader title="Decision Latency" sub="avg (solid) + p95 (dashed)" />
          {latTl?.length
            ? <LatencyChart data={latTl} />
            : <EmptyState message="No latency data yet" />
          }
        </Card>
      </div>

      {/* ── Charts row 2 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Card>
          <SectionHeader title="LLM Cost" sub="USD per bucket" />
          {costTl?.length
            ? <CostChart data={costTl} />
            : <EmptyState message="No LLM cost data yet" />
          }
        </Card>
        <Card>
          <SectionHeader title="Conflict Activity" sub="count per bucket" />
          {conflTl?.length
            ? <ConflictChart data={conflTl} />
            : <EmptyState message="No conflict data yet" />
          }
        </Card>
      </div>

      {/* ── Agent table ── */}
      {agents && agents.length > 0 && (
        <Card padding={0}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
            <SectionHeader title="Active Agents" sub="sorted by decision volume" />
          </div>
          <table className="ag-table">
            <thead>
              <tr>
                <th>Agent ID</th>
                <th>Decisions</th>
                <th>Avg Confidence</th>
                <th>Avg Latency</th>
                <th>Total Cost</th>
                <th>Tokens</th>
                <th>LLM Calls</th>
              </tr>
            </thead>
            <tbody>
              {agents.slice(0, 10).map((a) => (
                <tr key={a.agent_id}>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--blue)' }}>
                      {a.agent_id}
                    </span>
                  </td>
                  <td><span className="mono" style={{ fontSize: 12 }}>{fmtNumber(a.total_decisions)}</span></td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="mono" style={{ fontSize: 12, color: confidenceColor(a.avg_confidence), minWidth: 44 }}>
                        {fmtConfidence(a.avg_confidence)}
                      </span>
                      {a.avg_confidence !== null && (
                        <div className="conf-bar" style={{ width: 60 }}>
                          <div
                            className="conf-bar-fill"
                            style={{ width: `${(a.avg_confidence ?? 0) * 100}%`, background: confidenceColor(a.avg_confidence) }}
                          />
                        </div>
                      )}
                    </div>
                  </td>
                  <td><span className="mono" style={{ fontSize: 12, color: 'var(--amber)' }}>{fmtLatency(a.avg_latency_ms)}</span></td>
                  <td><span className="mono" style={{ fontSize: 12, color: 'var(--green)' }}>{fmtCost(a.total_cost_usd)}</span></td>
                  <td><span className="mono" style={{ fontSize: 12 }}>{fmtTokens(a.total_tokens)}</span></td>
                  <td><span className="mono" style={{ fontSize: 12 }}>{fmtNumber(a.total_llm_calls)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
