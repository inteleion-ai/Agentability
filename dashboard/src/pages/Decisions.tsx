import { useState } from 'react'
import { Card, Badge, SectionHeader, ErrorState } from '../components/ui/Card'
import { useDecisions, useDecision } from '../hooks/useApi'
import { fmtConfidence, fmtLatency, fmtCost, fmtTokens, fmtRelTime, confidenceColor, truncate } from '../utils/format'
import type { Decision } from '../types'

const DECISION_TYPES = [
  'classification','regression','generation','retrieval','planning',
  'execution','delegation','coordination','routing','tool_selection',
]

interface DecisionsProps { timeWindow: number }

// ── Detail side-panel ──────────────────────────────────────────────────────

function DetailPanel({ decision, onClose }: { decision: Decision; onClose: () => void }) {
  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, width: 480, height: '100vh',
      background: 'var(--bg-surface)', borderLeft: '1px solid var(--border)',
      zIndex: 100, overflowY: 'auto', padding: 20,
      display: 'flex', flexDirection: 'column', gap: 16,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Decision Detail</div>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}
        >×</button>
      </div>

      <div style={{ padding: 12, background: 'var(--bg-elevated)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Row label="Decision ID" value={decision.decision_id} mono />
        <Row label="Agent ID"    value={decision.agent_id} mono />
        {decision.session_id && (
          <Row label="Session (AFMX)" value={decision.session_id} mono />
        )}
        <Row label="Type"       value={decision.decision_type} />
        <Row label="Timestamp"  value={fmtRelTime(decision.timestamp)} />
        <Row label="Confidence" value={fmtConfidence(decision.confidence)} valueColor={confidenceColor(decision.confidence)} mono />
        <Row label="Latency"    value={fmtLatency(decision.latency_ms)} mono />
        <Row label="LLM Calls"  value={String(decision.llm_calls)} mono />
        <Row label="Tokens"     value={fmtTokens(decision.total_tokens)} mono />
        <Row label="Cost"       value={fmtCost(decision.total_cost_usd)} mono />
      </div>

      {/* AFMX session link — shown when session_id looks like a UUID (AFMX execution_id) */}
      {decision.session_id && /^[0-9a-f-]{36}$/.test(decision.session_id) && (
        <div style={{
          padding: '10px 12px',
          background: 'rgba(79,156,248,0.08)',
          border: '1px solid rgba(79,156,248,0.25)',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          fontSize: 12,
        }}>
          <div style={{ flex: 1, color: 'var(--text-secondary)' }}>
            <span style={{ color: 'var(--blue)', fontWeight: 600 }}>AFMX execution</span>
            {' — view all nodes in this matrix run'}
          </div>
          <button
            onClick={() => {
              /* filter the decision list by this session_id */
              window.dispatchEvent(new CustomEvent('afmx-filter-session', { detail: decision.session_id }))
              onClose()
            }}
            style={{
              background: 'var(--blue-dim)', border: '1px solid rgba(79,156,248,0.3)',
              borderRadius: 6, color: 'var(--blue)', fontSize: 11, fontWeight: 600,
              padding: '4px 10px', cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            Filter to session
          </button>
        </div>
      )}

      {decision.reasoning.length > 0 && (
        <Section title="Reasoning Chain">
          {decision.reasoning.map((step, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
              <span style={{ color: 'var(--blue)', fontFamily: 'var(--font-mono)', fontSize: 11, minWidth: 20, marginTop: 1 }}>
                {i + 1}.
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{step}</span>
            </div>
          ))}
        </Section>
      )}

      {decision.uncertainties.length > 0 && (
        <Section title="Uncertainties">
          {decision.uncertainties.map((u, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--amber)', marginBottom: 4 }}>⚠ {u}</div>
          ))}
        </Section>
      )}

      {decision.assumptions.length > 0 && (
        <Section title="Assumptions">
          {decision.assumptions.map((a, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>· {a}</div>
          ))}
        </Section>
      )}

      {decision.constraints_checked.length > 0 && (
        <Section title="Constraints Checked">
          {decision.constraints_checked.map((c, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--green)', marginBottom: 4 }}>✓ {c}</div>
          ))}
        </Section>
      )}

      {decision.constraints_violated.length > 0 && (
        <Section title="Constraints Violated">
          {decision.constraints_violated.map((c, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--red)', marginBottom: 4 }}>✗ {c}</div>
          ))}
        </Section>
      )}

      {decision.data_sources.length > 0 && (
        <Section title="Data Sources">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {decision.data_sources.map((s, i) => <Badge key={i} variant="blue">{s}</Badge>)}
          </div>
        </Section>
      )}

      {decision.tags.length > 0 && (
        <Section title="Tags">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {decision.tags.map((t, i) => <Badge key={i} variant="muted">{t}</Badge>)}
          </div>
        </Section>
      )}
    </div>
  )
}

function Row({ label, value, mono, valueColor }: { label: string; value: string; mono?: boolean; valueColor?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
      <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>{label}</span>
      <span style={{
        fontSize: 12, color: valueColor ?? 'var(--text-primary)',
        fontFamily: mono ? 'var(--font-mono)' : undefined,
        textAlign: 'right', wordBreak: 'break-all',
      }}>{value}</span>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function Decisions({ timeWindow }: DecisionsProps) {
  const [agentFilter,   setAgentFilter]   = useState('')
  const [sessionFilter, setSessionFilter] = useState('')
  const [typeFilter,    setTypeFilter]    = useState('')
  const [page,          setPage]          = useState(0)
  const [selected,      setSelected]      = useState<Decision | null>(null)
  const limit = 25

  // Listen for "Filter to session" events from the detail panel
  useState(() => {
    const handler = (e: Event) => {
      const id = (e as CustomEvent<string>).detail
      setSessionFilter(id)
      setAgentFilter('')
      setTypeFilter('')
      setPage(0)
    }
    window.addEventListener('afmx-filter-session', handler)
    return () => window.removeEventListener('afmx-filter-session', handler)
  })

  const { data, isLoading, error } = useDecisions({
    agent_id:      agentFilter   || undefined,
    session_id:    sessionFilter || undefined,
    decision_type: typeFilter    || undefined,
    limit,
    offset: page * limit,
  })

  const hasFilter = !!(agentFilter || sessionFilter || typeFilter)

  if (error) return <ErrorState message="Failed to load decisions." />

  return (
    <div className="fade-up">
      {selected && <DetailPanel decision={selected} onClose={() => setSelected(null)} />}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          value={agentFilter}
          onChange={(e) => { setAgentFilter(e.target.value); setPage(0) }}
          placeholder="Agent ID…"
          style={{
            background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8,
            color: 'var(--text-primary)', padding: '7px 12px', fontSize: 12, width: 200,
            fontFamily: 'var(--font-mono)', outline: 'none',
          }}
        />
        <input
          value={sessionFilter}
          onChange={(e) => { setSessionFilter(e.target.value); setPage(0) }}
          placeholder="Session / AFMX execution ID…"
          style={{
            background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8,
            color: sessionFilter ? 'var(--blue)' : 'var(--text-primary)',
            padding: '7px 12px', fontSize: 12, width: 270,
            fontFamily: 'var(--font-mono)', outline: 'none',
          }}
        />
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(0) }}
          style={{
            background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8,
            color: 'var(--text-primary)', padding: '7px 12px', fontSize: 12, outline: 'none',
          }}
        >
          <option value="">All types</option>
          {DECISION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>

        {hasFilter && (
          <button
            onClick={() => { setAgentFilter(''); setSessionFilter(''); setTypeFilter(''); setPage(0) }}
            style={{
              background: 'none', border: '1px solid var(--border)', borderRadius: 8,
              color: 'var(--text-muted)', padding: '7px 12px', fontSize: 12, cursor: 'pointer',
            }}
          >
            Clear
          </button>
        )}

        {/* Session context banner */}
        {sessionFilter && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px',
            background: 'var(--blue-dim)', border: '1px solid rgba(79,156,248,0.3)',
            borderRadius: 6, fontSize: 11, color: 'var(--blue)', fontWeight: 600,
          }}>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <rect x="1" y="1" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M3 5h4M3 3h4M3 7h2" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
            </svg>
            AFMX session
          </div>
        )}

        <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
          {data?.meta.total ?? 0} total
        </div>
      </div>

      {/* Table */}
      <Card padding={0}>
        <table className="ag-table">
          <thead>
            <tr>
              <th>Agent</th>
              <th>Type</th>
              <th>Confidence</th>
              <th>Latency</th>
              <th>LLM Calls</th>
              <th>Cost</th>
              <th>Violations</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j}><div className="skeleton" style={{ height: 14, width: '80%' }} /></td>
                    ))}
                  </tr>
                ))
              : data?.items.map((d) => (
                  <tr key={d.decision_id} onClick={() => setSelected(d)} style={{ cursor: 'pointer' }}>
                    <td>
                      <span className="mono" style={{ fontSize: 12, color: 'var(--blue)' }}>
                        {truncate(d.agent_id, 28)}
                      </span>
                      {d.session_id && (
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                          {truncate(d.session_id, 16)}
                        </div>
                      )}
                    </td>
                    <td><Badge variant="muted">{d.decision_type}</Badge></td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span className="mono" style={{ fontSize: 12, color: confidenceColor(d.confidence), minWidth: 42 }}>
                          {fmtConfidence(d.confidence)}
                        </span>
                        <div className="conf-bar" style={{ width: 48 }}>
                          <div className="conf-bar-fill" style={{
                            width: `${(d.confidence ?? 0) * 100}%`,
                            background: confidenceColor(d.confidence),
                          }} />
                        </div>
                      </div>
                    </td>
                    <td><span className="mono" style={{ fontSize: 12, color: 'var(--amber)' }}>{fmtLatency(d.latency_ms)}</span></td>
                    <td><span className="mono" style={{ fontSize: 12 }}>{d.llm_calls}</span></td>
                    <td><span className="mono" style={{ fontSize: 12, color: 'var(--green)' }}>{fmtCost(d.total_cost_usd)}</span></td>
                    <td>
                      {d.constraints_violated.length > 0
                        ? <Badge variant="red">{d.constraints_violated.length} violation{d.constraints_violated.length > 1 ? 's' : ''}</Badge>
                        : <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>—</span>
                      }
                    </td>
                    <td>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {fmtRelTime(d.timestamp)}
                      </span>
                    </td>
                  </tr>
                ))
            }
            {!isLoading && data?.items.length === 0 && (
              <tr><td colSpan={8}><div className="empty-state">No decisions found</div></td></tr>
            )}
          </tbody>
        </table>
      </Card>

      {/* Pagination */}
      {(data?.meta.total ?? 0) > limit && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 10, marginTop: 12 }}>
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8,
              color: 'var(--text-secondary)', padding: '6px 14px', fontSize: 12,
              cursor: page === 0 ? 'not-allowed' : 'pointer', opacity: page === 0 ? 0.4 : 1,
            }}
          >← Prev</button>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {page * limit + 1}–{Math.min((page + 1) * limit, data?.meta.total ?? 0)} of {data?.meta.total}
          </span>
          <button
            disabled={(page + 1) * limit >= (data?.meta.total ?? 0)}
            onClick={() => setPage((p) => p + 1)}
            style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8,
              color: 'var(--text-secondary)', padding: '6px 14px', fontSize: 12,
              cursor: (page + 1) * limit >= (data?.meta.total ?? 0) ? 'not-allowed' : 'pointer',
              opacity: (page + 1) * limit >= (data?.meta.total ?? 0) ? 0.4 : 1,
            }}
          >Next →</button>
        </div>
      )}
    </div>
  )
}
