import { Card, StatCard, SectionHeader, Badge, ErrorState } from '../components/ui/Card'
import { ConflictChart } from '../components/charts/Charts'
import { useConflicts, useConflictHotspots, useConflictTimeline, useConflictSummary } from '../hooks/useApi'
import { fmtRelTime, fmtNumber } from '../utils/format'

interface ConflictsProps { timeWindow: number }

function SeverityBar({ value }: { value: number }) {
  const color = value >= 0.8 ? 'var(--red)' : value >= 0.5 ? 'var(--amber)' : 'var(--green)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div className="conf-bar" style={{ width: 60 }}>
        <div className="conf-bar-fill" style={{ width: `${value * 100}%`, background: color }} />
      </div>
      <span className="mono" style={{ fontSize: 11, color }}>{(value * 100).toFixed(0)}%</span>
    </div>
  )
}

export default function Conflicts({ timeWindow }: ConflictsProps) {
  const { data: summary } = useConflictSummary(timeWindow)
  const { data: conflicts, isLoading, error } = useConflicts({ hours: timeWindow, limit: 100 })
  const { data: hotspots } = useConflictHotspots(timeWindow)
  const { data: timeline } = useConflictTimeline(timeWindow)

  if (error) return <ErrorState message="Failed to load conflicts." />

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <StatCard label="Total Conflicts" value={fmtNumber(summary?.total ?? 0)} color="var(--red)" />
        <StatCard label="Unresolved" value={fmtNumber(summary?.unresolved ?? 0)} color={summary?.unresolved ? 'var(--amber)' : 'var(--green)'} />
        <StatCard label="Resolved" value={fmtNumber(summary?.resolved ?? 0)} color="var(--green)" />
        <StatCard
          label="Avg Severity"
          value={summary?.avg_severity !== undefined ? `${(summary.avg_severity * 100).toFixed(0)}%` : '—'}
          color={summary?.avg_severity !== undefined ? (summary.avg_severity >= 0.7 ? 'var(--red)' : summary.avg_severity >= 0.4 ? 'var(--amber)' : 'var(--green)') : undefined}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* Timeline chart */}
        <Card>
          <SectionHeader title="Conflict Activity" sub="count over time" />
          {timeline?.length ? <ConflictChart data={timeline} /> : <div className="empty-state" style={{ height: 180 }}>No conflict data</div>}
        </Card>

        {/* Hotspot map */}
        <Card>
          <SectionHeader title="Conflict Hotspots" sub="agent pairs by frequency" />
          {hotspots?.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {hotspots.slice(0, 6).map((h, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {h.agents.map((a, j) => (
                        <Badge key={j} variant="blue">{a}</Badge>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>Conflicts</div>
                      <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--red)', textAlign: 'right' }}>{h.conflict_count}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>Avg Severity</div>
                      <div className="mono" style={{ fontSize: 12, color: h.avg_severity >= 0.7 ? 'var(--red)' : 'var(--amber)', textAlign: 'right' }}>
                        {(h.avg_severity * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state" style={{ height: 180 }}>No hotspot data</div>
          )}
        </Card>
      </div>

      {/* By type breakdown */}
      {summary?.by_type && Object.keys(summary.by_type).length > 0 && (
        <Card>
          <SectionHeader title="Conflict Types" />
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {Object.entries(summary.by_type).map(([type, count]) => (
              <div key={type} style={{ padding: '8px 14px', background: 'var(--bg-elevated)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{type.replace(/_/g, ' ')}</span>
                <span className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--red)' }}>{count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Table */}
      <Card padding={0}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
          <SectionHeader title="Recent Conflicts" sub={`last ${timeWindow}h`} />
        </div>
        <table className="ag-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Agents</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Strategy</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j}><div className="skeleton" style={{ height: 14, width: '80%' }} /></td>
                    ))}
                  </tr>
                ))
              : conflicts?.map((c) => (
                  <tr key={c.conflict_id}>
                    <td><Badge variant="muted">{c.conflict_type.replace(/_/g, ' ')}</Badge></td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {c.involved_agents.map((a, i) => <Badge key={i} variant="blue">{a}</Badge>)}
                      </div>
                    </td>
                    <td><SeverityBar value={c.severity} /></td>
                    <td>
                      {c.resolved
                        ? <Badge variant="green">Resolved</Badge>
                        : <Badge variant="amber">Open</Badge>
                      }
                    </td>
                    <td>
                      {c.resolution_strategy
                        ? <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{c.resolution_strategy}</span>
                        : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>
                      }
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {fmtRelTime(c.timestamp)}
                      </span>
                    </td>
                  </tr>
                ))
            }
            {!isLoading && conflicts?.length === 0 && (
              <tr><td colSpan={6}><div className="empty-state">No conflicts in this window</div></td></tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
