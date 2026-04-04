/** Formatting utilities */

export function fmtConfidence(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return `${(v * 100).toFixed(1)}%`
}

export function fmtLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—'
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`
  return `${ms.toFixed(0)}ms`
}

export function fmtCost(usd: number | null | undefined): string {
  if (usd === null || usd === undefined) return '—'
  if (usd < 0.001) return `$${(usd * 100000).toFixed(2)}μ`
  if (usd < 1) return `$${usd.toFixed(4)}`
  return `$${usd.toFixed(2)}`
}

export function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export function fmtRelTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000) return 'just now'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return `${Math.floor(diff / 86_400_000)}d ago`
}

export function fmtPercent(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

export function fmtNumber(n: number): string {
  return n.toLocaleString()
}

export function severityColor(s: string): string {
  const map: Record<string, string> = {
    critical: 'var(--red)',
    high: 'var(--amber)',
    medium: 'var(--blue)',
    low: 'var(--green)',
    none: 'var(--text-muted)',
  }
  return map[s?.toLowerCase()] ?? 'var(--text-muted)'
}

export function confidenceColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return 'var(--text-muted)'
  if (v >= 0.8) return 'var(--green)'
  if (v >= 0.6) return 'var(--amber)'
  return 'var(--red)'
}

export function severityBadgeClass(s: string): string {
  const map: Record<string, string> = {
    critical: 'badge-critical',
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
  }
  return map[s?.toLowerCase()] ?? 'badge-none'
}

export function truncate(s: string, n = 40): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}
