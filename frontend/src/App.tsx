import { useEffect, useState } from 'react'
import { checkConnection, type Connection } from './api'
import TicketDashboard from './TicketDashboard'

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
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${colors[connection.state]}`}>
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
          {labels[connection.state]}
        </span>
      </div>
      <p className="mt-6 text-sm leading-6 text-slate-600">{connection.message}</p>
      {connection.model && <p className="mt-3 font-mono text-xs text-slate-500">{connection.model}</p>}
    </section>
  )
}

export default function App() {
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
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <a href="/" className="flex items-center gap-3 rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600">
            <span aria-hidden="true" className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-lg font-bold text-white">O</span>
            <span className="text-lg font-semibold tracking-tight">OpsPilot</span>
          </a>
          <span className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-500">Local workspace</span>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-12 sm:py-16">
        <p className="text-xs font-semibold uppercase tracking-widest text-indigo-600">Customer support workspace</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Support dashboard</h1>
            <p className="mt-3 max-w-xl text-base leading-7 text-slate-500">Understand every customer message. Classify, prioritize, and review tickets with AI running locally.</p>
          </div>
          <button type="button" disabled={refreshing} onClick={() => { setRefreshing(true); setRefreshKey(key => key + 1) }}
            className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600 disabled:cursor-wait disabled:opacity-60">
            {refreshing ? 'Checking…' : 'Check again'}
          </button>
        </div>
        <div role="status" aria-live="polite" aria-busy={refreshing} className="mt-9 grid gap-5 md:grid-cols-2">
          <StatusCard title="Backend" subtitle="FastAPI · SQLite" connection={backend} />
          <StatusCard title="Local AI" subtitle="Ollama" connection={ollama} />
        </div>
        <p className="mt-5 text-xs text-slate-500">{checkedAt ? `Last checked at ${checkedAt.toLocaleTimeString()}. ` : ''}Refreshes automatically 15 seconds after each check.</p>
        <TicketDashboard />
      </main>
    </div>
  )
}
