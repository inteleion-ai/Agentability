import { Card, StatCard, SectionHeader, Badge, ErrorState } from '../components/ui/Card'
import { CostChart, ModelPieChart, LatencyChart } from '../components/charts/Charts'
import { useCost, useCostTimeline, useLatency, useLatencyTimeline } from '../hooks/useApi'
import { fmtCost, fmtTokens, fmtNumber, fmtLatency } from '../utils/format'

interface CostProps { timeWindow: number }

export default function Cost({ timeWindow }: CostProps) {
  const { data: cost, error: costErr } = useCost(timeWindow)
  const { data: costTl } = useCostTimeline(timeWindow)
  const { data: latency } = useLatency(undefined, timeWindow)
  const { data: latTl } = useLatencyTimeline(undefined, timeWindow)

  if (costErr) return <ErrorState message="Failed to load cost data." />

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <StatCard
          label="Total Spend"
          value={fmtCost(cost?.total_cost_usd)}
          color="var(--green)"
          sub={`last ${timeWindow}h`}
        />
        <StatCard
          label="Total Tokens"
          value={fmtTokens(cost?.total_tokens ?? 0)}
          color="var(--blue)"
          sub={`${fmtNumber(cost?.total_calls ?? 0)} calls`}
        />
        <StatCard
          label="Cost / Decision"
          value={fmtCost(cost?.cost_per_decision)}
          color="var(--purple)"
          sub="avg across agents"
        />
        <StatCard
          label="Avg Latency"
          value={fmtLatency(latency?.avg)}
          color="var(--amber)"
          sub={`p95: ${fmtLatency(latency?.p95)}`}
        />
      </div>

      {/* Cost timeline + pie */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
        <Card>
          <SectionHeader title="Cost Over Time" sub="USD per time bucket" />
          {costTl?.length ? <CostChart data={costTl} /> : <div className="empty-state" style={{ height: 180 }}>No cost data</div>}
        </Card>
        <Card>
          <SectionHeader title="Cost by Model" />
          {cost?.by_model && Object.keys(cost.by_model).length > 0
            ? <ModelPieChart data={cost.by_model} />
            : <div className="empty-state" style={{ height: 200 }}>No model data</div>
          }
        </Card>
      </div>

      {/* Latency chart */}
      <Card>
        <SectionHeader title="Latency (avg + p95)" sub="decision processing time" />
        {latTl?.length ? <LatencyChart data={latTl} /> : <div className="empty-state" style={{ height: 180 }}>No latency data</div>}
      </Card>

      {/* Latency percentiles */}
      {latency && (
        <Card>
          <SectionHeader title="Latency Percentiles" />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'p50 (median)', value: fmtLatency(latency.p50), color: 'var(--green)' },
              { label: 'p95', value: fmtLatency(latency.p95), color: 'var(--amber)' },
              { label: 'p99', value: fmtLatency(latency.p99), color: 'var(--red)' },
              { label: 'Average', value: fmtLatency(latency.avg), color: 'var(--blue)' },
            ].map((row) => (
              <div key={row.label} style={{ textAlign: 'center', padding: '16px 12px', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 700, fontFamily: 'var(--font-mono)', color: row.color, marginBottom: 6 }}>
                  {row.value}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  {row.label}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
            Based on {fmtNumber(latency.count)} decisions
          </div>
        </Card>
      )}

      {/* By model table */}
      {cost?.by_model && Object.keys(cost.by_model).length > 0 && (
        <Card padding={0}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
            <SectionHeader title="Cost Breakdown by Model" />
          </div>
          <table className="ag-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Total Cost</th>
                <th>% of Spend</th>
                <th>Cost Bar</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(cost.by_model)
                .sort(([, a], [, b]) => b - a)
                .map(([model, costVal]) => {
                  const pct = cost.total_cost_usd > 0 ? costVal / cost.total_cost_usd : 0
                  return (
                    <tr key={model}>
                      <td>
                        <span className="mono" style={{ fontSize: 12, color: 'var(--blue)' }}>{model}</span>
                      </td>
                      <td>
                        <span className="mono" style={{ fontSize: 12, color: 'var(--green)' }}>{fmtCost(costVal)}</span>
                      </td>
                      <td>
                        <span className="mono" style={{ fontSize: 12 }}>{(pct * 100).toFixed(1)}%</span>
                      </td>
                      <td>
                        <div className="conf-bar" style={{ width: 120 }}>
                          <div className="conf-bar-fill" style={{ width: `${pct * 100}%`, background: 'var(--green)' }} />
                        </div>
                      </td>
                    </tr>
                  )
                })
              }
            </tbody>
          </table>
        </Card>
      )}

      {/* By provider */}
      {cost?.by_provider && Object.keys(cost.by_provider).length > 0 && (
        <Card>
          <SectionHeader title="Cost by Provider" />
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {Object.entries(cost.by_provider).map(([provider, costVal]) => (
              <div key={provider} style={{ padding: '12px 20px', background: 'var(--bg-elevated)', borderRadius: 8, textAlign: 'center' }}>
                <div className="mono" style={{ fontSize: 18, fontWeight: 700, color: 'var(--green)', marginBottom: 4 }}>
                  {fmtCost(costVal)}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' }}>{provider}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
