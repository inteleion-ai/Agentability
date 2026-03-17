import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  ReferenceLine,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import type { TimelinePoint } from '../../types'

// ─── Shared chart constants ────────────────────────────────────────────────

const GRID_PROPS = { stroke: 'var(--border)', strokeDasharray: '3 3' }
const AXIS_TICK  = { fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }
const TOOLTIP_STYLE = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  fontSize: 12,
  color: 'var(--text-primary)',
}

function fmtTick(iso: string): string {
  try { return format(parseISO(iso), 'HH:mm') } catch { return iso }
}
function fmtLabel(iso: string): string {
  try { return format(parseISO(iso), 'MMM d HH:mm') } catch { return iso }
}

// ─── ConfidenceChart ──────────────────────────────────────────────────────

export function ConfidenceChart({
  data,
  height = 200,
  showMin = true,
}: {
  data: TimelinePoint[]
  height?: number
  showMin?: boolean
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="var(--blue)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--blue)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid {...GRID_PROPS} />
        <XAxis dataKey="timestamp" tickFormatter={fmtTick} tick={AXIS_TICK} tickLine={false} axisLine={false} />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          tick={AXIS_TICK}
          tickLine={false}
          axisLine={false}
        />
        <ReferenceLine y={0.7} stroke="var(--amber)" strokeDasharray="4 3" strokeWidth={1} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: number, name: string) => [
            `${(v * 100).toFixed(1)}%`,
            name === 'avg_confidence' ? 'Avg Confidence' : 'Min Confidence',
          ]}
          labelFormatter={fmtLabel}
        />
        <Area
          type="monotone"
          dataKey="avg_confidence"
          stroke="var(--blue)"
          strokeWidth={2}
          fill="url(#confGrad)"
          dot={false}
          activeDot={{ r: 4, fill: 'var(--blue)' }}
        />
        {showMin && (
          <Area
            type="monotone"
            dataKey="min_confidence"
            stroke="var(--red)"
            strokeWidth={1.2}
            fill="none"
            dot={false}
            strokeDasharray="3 3"
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  )
}

// ─── LatencyChart ─────────────────────────────────────────────────────────

export function LatencyChart({
  data,
  height = 200,
}: {
  data: TimelinePoint[]
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid {...GRID_PROPS} />
        <XAxis dataKey="timestamp" tickFormatter={fmtTick} tick={AXIS_TICK} tickLine={false} axisLine={false} />
        <YAxis
          tickFormatter={(v: number) => `${v.toFixed(0)}ms`}
          tick={AXIS_TICK}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: number, name: string) => [
            `${v.toFixed(1)}ms`,
            name === 'avg_latency_ms' ? 'Avg' : 'p95',
          ]}
          labelFormatter={fmtLabel}
        />
        <Line
          type="monotone"
          dataKey="avg_latency_ms"
          stroke="var(--amber)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: 'var(--amber)' }}
          name="avg_latency_ms"
        />
        <Line
          type="monotone"
          dataKey="p95_latency_ms"
          stroke="var(--red)"
          strokeWidth={1.5}
          dot={false}
          strokeDasharray="4 2"
          name="p95_latency_ms"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ─── CostChart ────────────────────────────────────────────────────────────

export function CostChart({
  data,
  height = 200,
}: {
  data: TimelinePoint[]
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid {...GRID_PROPS} />
        <XAxis dataKey="timestamp" tickFormatter={fmtTick} tick={AXIS_TICK} tickLine={false} axisLine={false} />
        <YAxis
          tickFormatter={(v: number) => `$${v.toFixed(4)}`}
          tick={AXIS_TICK}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: number) => [`$${v.toFixed(6)}`, 'Cost USD']}
          labelFormatter={fmtLabel}
        />
        <Bar dataKey="cost_usd" fill="var(--green)" radius={[3, 3, 0, 0]} name="Cost USD" />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── ConflictChart ────────────────────────────────────────────────────────

export function ConflictChart({
  data,
  height = 200,
}: {
  data: TimelinePoint[]
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid {...GRID_PROPS} />
        <XAxis dataKey="timestamp" tickFormatter={fmtTick} tick={AXIS_TICK} tickLine={false} axisLine={false} />
        <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: number) => [v, 'Conflicts']}
          labelFormatter={fmtLabel}
        />
        <Bar dataKey="count" fill="var(--red)" radius={[3, 3, 0, 0]} name="Conflicts" />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── ModelPieChart ────────────────────────────────────────────────────────

const PIE_COLORS = [
  'var(--blue)',
  'var(--green)',
  'var(--amber)',
  'var(--purple)',
  'var(--cyan)',
  'var(--red)',
]

export function ModelPieChart({
  data,
  height = 220,
}: {
  data: Record<string, number>
  height?: number
}) {
  const entries = Object.entries(data)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value]) => ({ name, value }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={entries}
          cx="50%"
          cy="45%"
          outerRadius={72}
          innerRadius={42}
          dataKey="value"
          strokeWidth={0}
          paddingAngle={2}
        >
          {entries.map((_, i) => (
            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: number) => [`$${v.toFixed(5)}`, 'Cost']}
        />
        <Legend
          iconType="circle"
          iconSize={7}
          wrapperStyle={{
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
            paddingTop: 8,
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ─── MiniSparkline (for tables / inline) ──────────────────────────────────

export function MiniSparkline({
  values,
  color = 'var(--blue)',
  height = 32,
  width = 80,
}: {
  values: number[]
  color?: string
  height?: number
  width?: number
}) {
  if (!values.length) return null
  const data = values.map((v, i) => ({ i, v }))
  return (
    <ResponsiveContainer width={width} height={height}>
      <LineChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
        <Line
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
