import { useState } from 'react'
import { Card, StatCard, SectionHeader, Badge, ErrorState } from '../components/ui/Card'
import { ConfidenceChart, LatencyChart } from '../components/charts/Charts'
import { useAgents, useAgentDrift, useAgentTimeline, useLatencyTimeline } from '../hooks/useApi'
import { fmtConfidence, fmtLatency, fmtCost, fmtTokens, fmtNumber, confidenceColor, severityColor, severityBadgeClass } from '../utils/format'

interface AgentsProps { timeWindow: number }

export default function Agents({ timeWindow }: AgentsProps) {
  const [selected, setSelected] = useState<string>('')
  const { data: agents, isLoading, error } = useAgents()
  const { data: drift } = useAgentDrift(selected)
  const { data: confTl } = useAgentTimeline(selected, timeWindow)
  const { data: latTl } = useLatencyTimeline(selected, timeWindow)

  if (error) return <ErrorState message="Failed to load agents." />

  const activeAgent = agents?.find((a) => a.agent_id === selected)

  return (
    <div className="fade-up" style={{ display: 'flex', gap: 16 }}>
      {/* Agent list */}
      <div style={{ width: 260, flexShrink: 0 }}>
        <Card padding={0}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
            {agents?.length ?? 0} Agents
          </div>
          <div style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
            {isLoading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <div className="skeleton" style={{ height: 13, width: '70%', marginBottom: 6 }} />
                    <div className="skeleton" style={{ height: 11, width: '40%' }} />
                  </div>
                ))
              : agents?.map((a) => (
                  <div
                    key={a.agent_id}
                    onClick={() => setSelected(a.agent_id)}
                    style={{
                      padding: '12px 16px',
                      borderBottom: '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      background: selected === a.agent_id ? 'var(--blue-dim)' : 'transparent',
                      borderLeft: selected === a.agent_id ? '2px solid var(--blue)' : '2px solid transparent',
                      transition: 'all 0.15s',
                    }}
                  >
                    <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: selected === a.agent_id ? 'var(--blue)' : 'var(--text-primary)', marginBottom: 4, wordBreak: 'break-all' }}>
                      {a.agent_id}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 11, color: confidenceColor(a.avg_confidence) }}>
                        {fmtConfidence(a.avg_confidence)}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {fmtNumber(a.total_decisions)} dec
                      </span>
                    </div>
                  </div>
                ))
            }
          </div>
        </Card>
      </div>

      {/* Right panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {!selected ? (
          <div className="empty-state" style={{ height: 300 }}>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none"><circle cx="20" cy="12" r="8" stroke="currentColor" strokeWidth="2"/><path d="M4 36c0-8.837 7.163-16 16-16s16 7.163 16 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>Select an agent to view details</div>
          </div>
        ) : (
          <>
            {/* Agent KPI row */}
            {activeAgent && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <StatCard label="Decisions" value={fmtNumber(activeAgent.total_decisions)} color="var(--blue)" />
                <StatCard label="Avg Confidence" value={fmtConfidence(activeAgent.avg_confidence)} color={confidenceColor(activeAgent.avg_confidence)} />
                <StatCard label="Avg Latency" value={fmtLatency(activeAgent.avg_latency_ms)} color="var(--amber)" />
                <StatCard label="Total Cost" value={fmtCost(activeAgent.total_cost_usd)} sub={`${fmtTokens(activeAgent.total_tokens)} tokens`} color="var(--green)" />
              </div>
            )}

            {/* Drift alert */}
            {drift && drift.drift_detected && (
              <div style={{
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--amber-dim)',
                border: '1px solid rgba(251,191,36,0.4)',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
              }}>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
                  <path d="M9 2L16.5 15H1.5L9 2z" stroke="var(--amber)" strokeWidth="1.5" strokeLinejoin="round"/>
                  <path d="M9 7v4M9 13v.5" stroke="var(--amber)" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--amber)', marginBottom: 4 }}>
                    Confidence Drift Detected — {drift.severity.toUpperCase()}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Baseline: <span className="mono" style={{ color: 'var(--text-primary)' }}>{fmtConfidence(drift.baseline_confidence)}</span>
                    {' → '}Current: <span className="mono" style={{ color: confidenceColor(drift.current_confidence) }}>{fmtConfidence(drift.current_confidence)}</span>
                    {' · '}Magnitude: <span className="mono" style={{ color: 'var(--amber)' }}>{drift.drift_magnitude !== undefined ? `${(drift.drift_magnitude * 100).toFixed(1)}%` : '—'}</span>
                  </div>
                  {drift.recommendation && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{drift.recommendation}</div>
                  )}
                </div>
              </div>
            )}

            {/* Charts */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Card>
                <SectionHeader title="Confidence Timeline" />
                {confTl?.length ? <ConfidenceChart data={confTl} /> : <div className="empty-state" style={{ height: 180 }}>No data</div>}
              </Card>
              <Card>
                <SectionHeader title="Latency Timeline" />
                {latTl?.length ? <LatencyChart data={latTl} /> : <div className="empty-state" style={{ height: 180 }}>No data</div>}
              </Card>
            </div>

            {/* Drift timeline detail */}
            {drift?.timeline && drift.timeline.length > 0 && (
              <Card>
                <SectionHeader title="Drift Observation Window" sub={`${drift.recent_samples ?? 0} recent vs ${drift.baseline_samples ?? 0} baseline samples`} />
                <div style={{ display: 'flex', gap: 20 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {[
                      { label: 'Current Avg', value: fmtConfidence(drift.current_confidence), color: confidenceColor(drift.current_confidence) },
                      { label: 'Baseline Avg', value: fmtConfidence(drift.baseline_confidence), color: 'var(--text-secondary)' },
                      { label: 'Drift', value: drift.drift_magnitude !== undefined ? `${(drift.drift_magnitude * 100).toFixed(2)}%` : '—', color: drift.drift_detected ? 'var(--amber)' : 'var(--green)' },
                      { label: 'Severity', value: drift.severity.toUpperCase(), color: severityColor(drift.severity) },
                    ].map((row) => (
                      <div key={row.label} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', width: 100 }}>{row.label}</span>
                        <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: row.color }}>{row.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  )
}
