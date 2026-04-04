import { NavLink } from 'react-router-dom'
import { useHealth } from '../../hooks/useApi'

const NAV = [
  {
    to: '/',
    label: 'Overview',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <rect x="1" y="1" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
        <rect x="8.5" y="1" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
        <rect x="1" y="8.5" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
        <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    ),
  },
  {
    to: '/decisions',
    label: 'Decisions',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <path d="M2 4h11M2 7.5h7M2 11h5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/agents',
    label: 'Agents',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="4.5" r="2.5" stroke="currentColor" strokeWidth="1.4" />
        <path d="M2 13c0-3.038 2.462-5.5 5.5-5.5S13 9.962 13 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/conflicts',
    label: 'Conflicts',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <path d="M7.5 1.5L13.5 12.5H1.5L7.5 1.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M7.5 6v3M7.5 11v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/cost',
    label: 'Cost & LLM',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="6" stroke="currentColor" strokeWidth="1.4" />
        <path
          d="M7.5 3.5v1m0 6v1M5 6a2 2 0 0 1 2-2h1a1.5 1.5 0 0 1 0 3H7a1.5 1.5 0 0 0 0 3h1a2 2 0 0 0 2-2"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
]

// AFMX dashboard URL — set VITE_AFMX_URL env var to point to your AFMX instance
const AFMX_URL = (() => {
  try {
    return (import.meta as { env?: Record<string, string> }).env?.VITE_AFMX_URL ?? 'http://localhost:8100'
  } catch {
    return 'http://localhost:8100'
  }
})()

export default function Sidebar() {
  const { data: health } = useHealth()
  const alive = health?.status === 'healthy'
  // AFMX feeds data via session_id — if decisions exist, AFMX is likely connected
  const afmxActive = (health?.total_decisions ?? 0) > 0

  return (
    <aside
      style={{
        width: 'var(--sidebar-w)',
        flexShrink: 0,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* ── Logo ── */}
      <div
        style={{
          height: 'var(--topbar-h)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '0 16px',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #4F9CF8 0%, #A78BFA 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            boxShadow: '0 2px 8px rgba(79,156,248,0.3)',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="2.5" fill="white" />
            <circle cx="2" cy="3.5" r="1.5" fill="white" opacity="0.75" />
            <circle cx="12" cy="3.5" r="1.5" fill="white" opacity="0.75" />
            <circle cx="2" cy="10.5" r="1.5" fill="white" opacity="0.5" />
            <circle cx="12" cy="10.5" r="1.5" fill="white" opacity="0.5" />
            <line x1="3.5" y1="4.2" x2="5.2" y2="5.8" stroke="white" strokeWidth="1" opacity="0.6" />
            <line x1="10.5" y1="4.2" x2="8.8" y2="5.8" stroke="white" strokeWidth="1" opacity="0.6" />
            <line x1="3.5" y1="9.8" x2="5.2" y2="8.2" stroke="white" strokeWidth="1" opacity="0.4" />
            <line x1="10.5" y1="9.8" x2="8.8" y2="8.2" stroke="white" strokeWidth="1" opacity="0.4" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
            Agentability
          </div>
          <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Intelligence Layer
          </div>
        </div>
      </div>

      {/* ── Nav ── */}
      <nav style={{ flex: 1, padding: '10px 8px', overflowY: 'auto' }}>
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            color: 'var(--text-muted)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            padding: '6px 10px 10px',
          }}
        >
          Observability
        </div>

        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 10px',
              borderRadius: 'var(--radius-md)',
              fontSize: 13,
              fontWeight: 500,
              textDecoration: 'none',
              marginBottom: 2,
              transition: 'all 0.12s ease',
              color: isActive ? 'var(--blue)' : 'var(--text-secondary)',
              background: isActive ? 'var(--blue-dim)' : 'transparent',
            })}
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}

        {/* ── Data sources section ── */}
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            color: 'var(--text-muted)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            padding: '14px 10px 8px',
          }}
        >
          Data Sources
        </div>

        {/* AFMX link */}
        <a
          href={AFMX_URL + '/afmx/ui'}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '8px 10px',
            borderRadius: 'var(--radius-md)',
            fontSize: 13,
            fontWeight: 500,
            textDecoration: 'none',
            marginBottom: 2,
            transition: 'all 0.12s ease',
            color: 'var(--text-secondary)',
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)' }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
        >
          {/* AFMX logo mark */}
          <div style={{
            width: 15, height: 15, borderRadius: 4,
            background: 'linear-gradient(135deg, var(--blue) 0%, var(--purple) 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, fontSize: 8, fontWeight: 800, color: '#fff',
          }}>
            AX
          </div>
          <span style={{ flex: 1 }}>AFMX Engine</span>
          {/* Connection indicator */}
          <span
            className={`status-dot ${afmxActive ? 'green' : 'muted'}`}
            title={afmxActive ? 'Data flowing from AFMX' : 'No AFMX data yet'}
          />
          {/* External link icon */}
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style={{ opacity: 0.4 }}>
            <path d="M1.5 8.5l7-7M5 1.5h3v3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </a>
      </nav>

      {/* ── Footer status ── */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexShrink: 0,
        }}
      >
        <span className={`status-dot ${alive ? 'green live-pulse' : 'red'}`} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)' }}>
            API {alive ? 'Connected' : 'Offline'}
          </div>
          {health && (
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              v{health.version} · {health.total_decisions.toLocaleString()} decisions
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}
