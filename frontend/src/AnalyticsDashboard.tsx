import { useEffect, useState } from 'react'
import { getAnalytics, statusLabels, type Analytics } from './api'

const labels: Record<string, string> = { delivery: 'Delivery', returns: 'Returns', payments: 'Payments', technical_support: 'Technical support', other: 'Other', ...statusLabels }
const card = 'min-w-0 rounded-xl border border-slate-200 bg-white p-5'

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const maximum = Math.max(1, ...Object.values(values))
  return <section aria-label={title} className={card}><h2 className="font-semibold text-slate-900">{title}</h2>
    <ul className="mt-4 space-y-3">{Object.entries(values).map(([key, value]) => <li key={key} className="text-sm">
      <div className="flex justify-between gap-3"><span className="capitalize text-slate-600">{labels[key] ?? key}</span><span className="font-semibold">{value}</span></div>
      <div aria-hidden="true" className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100"><div style={{ width: `${value / maximum * 100}%` }} className="h-full rounded-full bg-indigo-500" /></div>
    </li>)}</ul>
  </section>
}

export default function AnalyticsDashboard({ active }: { active: boolean }) {
  const [data, setData] = useState<Analytics | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    if (!active) return
    const controller = new AbortController()
    setLoading(true); setError('')
    void getAnalytics(controller.signal).then(value => { if (!controller.signal.aborted) setData(value) })
      .catch(() => { if (!controller.signal.aborted) setError('Cannot load analytics. Check the backend and refresh.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [active, revision])
  return <section aria-label="Analytics" className="mt-6 space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-xl font-semibold text-slate-950">Analytics</h1><p className="mt-1 text-xs text-slate-500">All tickets in this workspace · independent of inbox search and filters</p></div>
      <button disabled={loading} onClick={() => setRevision(value => value + 1)} className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50">Refresh analytics</button>
    </div>
    {loading && <p role="status" className="text-sm text-slate-500">Loading analytics…</p>}
    {error && <p role="alert" className="rounded-lg bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}
    {!loading && !error && data && <>
      {!data.total_tickets && <p className="rounded-lg bg-indigo-50 p-4 text-sm text-indigo-900">No tickets yet. Classify a customer message in the Smart Inbox to see activity here.</p>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[
        ['Total tickets', data.total_tickets], ['New tickets', data.by_status.new], ['Resolved tickets', data.by_status.resolved], ['Human review required', data.human_review_tickets],
      ].map(([title, value]) => <div className={card} key={title}><p className="text-xs font-medium text-slate-500">{title}</p><p className="mt-2 text-2xl font-semibold text-indigo-700">{value}</p></div>)}</div>
      <div className="grid gap-4 lg:grid-cols-3"><Distribution title="Tickets by category" values={data.by_category} /><Distribution title="Priority distribution" values={data.by_priority} /><Distribution title="Ticket status distribution" values={data.by_status} /></div>
      <section aria-label="Ticket volume over time" className={card}><h2 className="font-semibold text-slate-900">Ticket volume over time</h2><p className="mt-1 text-xs text-slate-500">Created per UTC calendar day · last {data.volume.length} days, including today</p>
        <div className="mt-4 overflow-x-auto"><div className="flex h-36 min-w-0 items-end gap-1" role="img" aria-label="Ticket creation volume; daily values are listed below">
          {data.volume.map(day => <div key={day.date} title={`${day.date}: ${day.count}`} className="flex h-full min-w-1 flex-1 items-end bg-slate-50"><div className="w-full rounded-t bg-indigo-500" style={{ height: `${day.count / Math.max(1, ...data.volume.map(value => value.count)) * 100}%` }} /></div>)}
        </div></div>
        <div className="mt-2 flex justify-between text-xs text-slate-500"><span>{data.volume[0]?.date}</span><span>{data.volume.at(-1)?.date}</span></div>
        <details className="mt-3 text-xs text-slate-600"><summary className="cursor-pointer">Daily ticket counts</summary><table className="mt-2 w-full text-left"><thead><tr><th>Date (UTC)</th><th>Tickets</th></tr></thead><tbody>{data.volume.map(day => <tr key={day.date}><td>{day.date}</td><td>{day.count}</td></tr>)}</tbody></table></details>
      </section>
      <div className="grid gap-4 md:grid-cols-2"><section aria-label="Draft decisions" className={card}><h2 className="font-semibold">Human review & draft decisions</h2><p className="mt-3 text-sm">Approved drafts: <strong>{data.draft_decisions.approved}</strong> · Rejected drafts: <strong>{data.draft_decisions.rejected}</strong></p><p className="mt-2 text-xs leading-5 text-slate-500">Each draft ID counts once by its current decision. Revision history is not counted as additional decisions. Human review flags remain active after documentation. Approval sends nothing.</p></section>
        <section aria-label="Resolution time" className={card}><h2 className="font-semibold">Average time to resolution</h2><p className="mt-3 text-xl font-semibold text-indigo-700">{data.resolution_time.average_seconds === null ? 'Not available yet' : `${(data.resolution_time.average_seconds / 3600).toFixed(1)} hours`}</p><p className="mt-2 text-xs leading-5 text-slate-500">Creation to latest recorded resolution for currently resolved tickets. {data.resolution_time.measured_tickets} measured; {data.resolution_time.unavailable_tickets} resolved tickets lack reliable timestamps. Reopened tickets are excluded.</p></section></div>
      <p className="text-xs text-slate-500">Calculated {new Date(data.generated_at).toLocaleString()}. Refresh to include recent changes.</p>
    </>}
  </section>
}
