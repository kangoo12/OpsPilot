import { useEffect, useState } from 'react'
import { checkConnection, type Connection } from './api'
import TicketDashboard from './TicketDashboard'
import AnalyticsDashboard from './AnalyticsDashboard'

const initial: Connection = { state: 'checking', message: 'Checking connection…' }

function StatusCard({ title, subtitle, connection }: {
  title: string
  subtitle: string
  connection: Connection
}) {
  const labels = { checking: 'Checking', connected: 'Connected', error: 'Needs attention' }
  const colors = {
    checking: 'bg-slate-100 text-slate-600',
    connected: 'bg-emerald-50 text-emerald-800',
    error: 'bg-amber-50 text-amber-900',
  }
  return (
    <section className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{title} <span className="ml-1 text-xs font-normal text-slate-500">{subtitle}</span></h2>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${colors[connection.state]}`}>
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
          {labels[connection.state]}
        </span>
      </div>
      {connection.state === 'error' && <p className="mt-2 text-xs leading-5 text-amber-900">{connection.message}</p>}
      {connection.model && <p className="mt-1 font-mono text-xs text-slate-500">{connection.model}</p>}
    </section>
  )
}

export default function App() {
  const [section, setSection] = useState<'inbox' | 'analytics'>('inbox')
  const [backend, setBackend] = useState<Connection>(initial)
  const [ollama, setOllama] = useState<Connection>(initial)
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(true)
  const [checkedAt, setCheckedAt] = useState<Date | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    async function refresh() {
      setRefreshing(true)
      const results = await Promise.all([
        checkConnection('backend', controller.signal),
        checkConnection('ollama', controller.signal),
      ])
      if (controller.signal.aborted) return
      setBackend(results[0])
      setOllama(results[1])
      setCheckedAt(new Date())
      setRefreshing(false)
      // Schedule after completion to avoid overlapping requests.
      timer = setTimeout(() => { void refresh() }, 15000)
    }
    void refresh()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [refreshKey])

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <a href="/" className="flex items-center gap-3 rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600">
            <span aria-hidden="true" className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-lg font-bold text-white">O</span>
            <span className="text-lg font-semibold tracking-tight">OpsPilot</span>
          </a>
          <span className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-500">Local workspace</span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav aria-label="Workspace navigation" className="flex gap-1 rounded-xl border border-slate-200 bg-white p-1">
            {(['inbox', 'analytics'] as const).map(value => <button key={value} type="button" aria-pressed={section === value} onClick={() => setSection(value)} className={`rounded-lg px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${section === value ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-indigo-50'}`}>{value === 'inbox' ? 'Smart Inbox' : 'Analytics'}</button>)}
          </nav>
          <button type="button" disabled={refreshing} onClick={() => { setRefreshing(true); setRefreshKey(key => key + 1) }} className="rounded-lg px-3 py-2 text-xs font-semibold text-indigo-700 outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50">{refreshing ? 'Checking?' : 'Check connections'}</button>
        </div>
        <div role="status" aria-live="polite" aria-busy={refreshing} className="mt-3 grid gap-2 md:grid-cols-2">
          <StatusCard title="Backend" subtitle="FastAPI · SQLite" connection={backend} />
          <StatusCard title="Local AI" subtitle="Ollama" connection={ollama} />
        </div>
        <p className="mt-2 text-xs text-slate-500">{checkedAt ? `Last checked at ${checkedAt.toLocaleTimeString()}. ` : ''}Refreshes automatically 15 seconds after each check.</p>
        <div hidden={section !== 'inbox'}><TicketDashboard /></div>
        <div hidden={section !== 'analytics'}><AnalyticsDashboard active={section === 'analytics'} /></div>
      </main>
    </div>
  )
}
