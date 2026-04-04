import { useLocation } from 'react-router-dom'

interface TopBarProps {
  timeWindow: number
  onTimeWindowChange: (hours: number) => void
}

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  '/':          { title: 'Overview',   subtitle: 'Real-time agent intelligence summary' },
  '/decisions': { title: 'Decisions',  subtitle: 'Decision trace explorer with full provenance' },
  '/agents':    { title: 'Agents',     subtitle: 'Per-agent performance, confidence drift & latency' },
  '/conflicts': { title: 'Conflicts',  subtitle: 'Multi-agent conflict analysis and hotspot map' },
  '/cost':      { title: 'Cost & LLM', subtitle: 'Token spend, model usage and cost analytics' },
}

const WINDOWS = [
  { label: '1h',  value: 1 },
  { label: '6h',  value: 6 },
  { label: '24h', value: 24 },
  { label: '7d',  value: 168 },
  { label: '30d', value: 720 },
]

export default function TopBar({ timeWindow, onTimeWindowChange }: TopBarProps) {
  const { pathname } = useLocation()
  const meta = PAGE_META[pathname] ?? { title: 'Agentability', subtitle: '' }

  return (
    <header
      style={{
        height: 'var(--topbar-h)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        flexShrink: 0,
        background: 'var(--bg-surface)',
        gap: 16,
      }}
    >
      {/* Page title */}
      <div>
        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.25 }}>
          {meta.title}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{meta.subtitle}</div>
      </div>

      {/* Time window pill selector */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          padding: 3,
        }}
      >
        {WINDOWS.map((w) => (
          <button
            key={w.value}
            onClick={() => onTimeWindowChange(w.value)}
            style={{
              padding: '4px 10px',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s',
              background: timeWindow === w.value ? 'var(--blue)' : 'transparent',
              color: timeWindow === w.value ? '#fff' : 'var(--text-muted)',
              boxShadow: timeWindow === w.value ? '0 1px 6px rgba(79,156,248,0.35)' : 'none',
            }}
          >
            {w.label}
          </button>
        ))}
      </div>
    </header>
  )
}
