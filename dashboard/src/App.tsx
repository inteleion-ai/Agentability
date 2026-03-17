import { useState } from 'react'
import { BrowserRouter, Routes, Route, Outlet, useOutletContext } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import Overview from './pages/Overview'
import Decisions from './pages/Decisions'
import Agents from './pages/Agents'
import Conflicts from './pages/Conflicts'
import Cost from './pages/Cost'

// ─── Query client ──────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

// ─── Outlet context type ───────────────────────────────────────────────────

interface LayoutCtx { timeWindow: number }
export function useTimeWindow(): number {
  return useOutletContext<LayoutCtx>().timeWindow
}

// ─── Shell layout ──────────────────────────────────────────────────────────

function Layout() {
  const [timeWindow, setTimeWindow] = useState(24)

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar timeWindow={timeWindow} onTimeWindowChange={setTimeWindow} />
        <main
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px 24px',
            background: 'var(--bg-base)',
          }}
        >
          <Outlet context={{ timeWindow } satisfies LayoutCtx} />
        </main>
      </div>
    </div>
  )
}

// ─── Route wrappers that consume timeWindow from context ──────────────────

function OverviewPage()   { return <Overview   timeWindow={useTimeWindow()} /> }
function DecisionsPage()  { return <Decisions  timeWindow={useTimeWindow()} /> }
function AgentsPage()     { return <Agents     timeWindow={useTimeWindow()} /> }
function ConflictsPage()  { return <Conflicts  timeWindow={useTimeWindow()} /> }
function CostPage()       { return <Cost       timeWindow={useTimeWindow()} /> }

// ─── App root ─────────────────────────────────────────────────────────────

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index       element={<OverviewPage />} />
            <Route path="decisions" element={<DecisionsPage />} />
            <Route path="agents"    element={<AgentsPage />} />
            <Route path="conflicts" element={<ConflictsPage />} />
            <Route path="cost"      element={<CostPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
