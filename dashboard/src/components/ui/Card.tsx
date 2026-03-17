import type { ReactNode, CSSProperties } from 'react'

// ─── Card ─────────────────────────────────────────────────────────────────

interface CardProps {
  children: ReactNode
  style?: CSSProperties
  className?: string
  padding?: number | string
  onClick?: () => void
}

export function Card({ children, style, className = '', padding = 16, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`card-glow ${className}`}
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding,
        cursor: onClick ? 'pointer' : undefined,
        transition: 'border-color 0.2s, box-shadow 0.2s',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

// ─── StatCard ─────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  color?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  icon?: ReactNode
}

export function StatCard({ label, value, sub, color, trend, trendValue, icon }: StatCardProps) {
  const trendColor =
    trend === 'up' ? 'var(--green)' : trend === 'down' ? 'var(--red)' : 'var(--text-muted)'
  const trendArrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.07em',
          }}
        >
          {label}
        </div>
        {icon && <div style={{ color: color ?? 'var(--text-muted)', opacity: 0.8 }}>{icon}</div>}
      </div>

      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          fontFamily: 'var(--font-mono)',
          color: color ?? 'var(--text-primary)',
          lineHeight: 1,
          marginBottom: 6,
        }}
      >
        {value}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {trendValue && (
          <span style={{ fontSize: 11, color: trendColor, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            {trendArrow} {trendValue}
          </span>
        )}
        {sub && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</span>}
      </div>
    </Card>
  )
}

// ─── Badge ────────────────────────────────────────────────────────────────

interface BadgeProps {
  children: ReactNode
  variant?: 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'cyan' | 'muted'
  size?: 'sm' | 'md'
}

export function Badge({ children, variant = 'muted', size = 'sm' }: BadgeProps) {
  const colors: Record<string, { bg: string; color: string; border: string }> = {
    blue:   { bg: 'rgba(79,156,248,0.12)',  color: 'var(--blue)',       border: 'rgba(79,156,248,0.3)' },
    green:  { bg: 'rgba(52,211,153,0.10)',  color: 'var(--green)',      border: 'rgba(52,211,153,0.3)' },
    amber:  { bg: 'rgba(251,191,36,0.12)',  color: 'var(--amber)',      border: 'rgba(251,191,36,0.3)' },
    red:    { bg: 'rgba(248,113,113,0.12)', color: 'var(--red)',        border: 'rgba(248,113,113,0.3)' },
    purple: { bg: 'rgba(167,139,250,0.12)', color: 'var(--purple)',     border: 'rgba(167,139,250,0.3)' },
    cyan:   { bg: 'rgba(34,211,238,0.10)',  color: 'var(--cyan)',       border: 'rgba(34,211,238,0.3)' },
    muted:  { bg: 'rgba(85,94,120,0.15)',   color: 'var(--text-muted)', border: 'var(--border)' },
  }
  const c = colors[variant] ?? colors.muted

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: size === 'sm' ? '2px 7px' : '4px 10px',
        borderRadius: 99,
        fontSize: size === 'sm' ? 11 : 12,
        fontWeight: 600,
        fontFamily: 'var(--font-mono)',
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.border}`,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────

export function Skeleton({ w = '100%', h = 20 }: { w?: string | number; h?: string | number }) {
  return <div className="skeleton" style={{ width: w, height: h, borderRadius: 6 }} />
}

// ─── SectionHeader ────────────────────────────────────────────────────────

interface SectionHeaderProps {
  title: string
  sub?: string
  action?: ReactNode
}

export function SectionHeader({ title, sub, action }: SectionHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 14,
      }}
    >
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</div>
        {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
      </div>
      {action}
    </div>
  )
}

// ─── ErrorState ───────────────────────────────────────────────────────────

export function ErrorState({ message }: { message: string }) {
  return (
    <div
      style={{
        padding: '20px 24px',
        borderRadius: 'var(--radius-md)',
        background: 'var(--red-dim)',
        border: '1px solid rgba(248,113,113,0.3)',
        color: 'var(--red)',
        fontSize: 13,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5" />
        <path d="M8 5v4M8 11v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      {message}
    </div>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────

export function EmptyState({ message = 'No data available' }: { message?: string }) {
  return (
    <div className="empty-state">
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
        <circle cx="18" cy="18" r="16" stroke="currentColor" strokeWidth="1.5" />
        <path d="M12 18h12M18 12v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
      </svg>
      <span style={{ fontSize: 13 }}>{message}</span>
    </div>
  )
}

// ─── Divider ──────────────────────────────────────────────────────────────

export function Divider({ my = 16 }: { my?: number }) {
  return <div style={{ height: 1, background: 'var(--border)', margin: `${my}px 0` }} />
}

// ─── Spinner ──────────────────────────────────────────────────────────────

export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      style={{ animation: 'spin 0.8s linear infinite' }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <circle cx="12" cy="12" r="9" stroke="var(--border)" strokeWidth="2" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="var(--blue)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
