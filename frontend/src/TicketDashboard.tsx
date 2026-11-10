import { useEffect, useRef, useState, type FormEvent } from 'react'
import { createTicket, getTicket, listTickets, MAX_MESSAGE_LENGTH, type Category, type Priority, type Ticket, type TicketPage } from './api'

const categoryLabels: Record<Category, string> = {
  delivery: 'Delivery', returns: 'Returns', payments: 'Payments', technical_support: 'Technical support', other: 'Other',
}
const priorityColors: Record<Priority, string> = {
  low: 'bg-slate-100 text-slate-700', medium: 'bg-blue-50 text-blue-800',
  high: 'bg-amber-50 text-amber-900', urgent: 'bg-rose-50 text-rose-800',
}
const button = 'rounded-lg px-4 py-2.5 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-50'
const secondaryButton = `${button} border border-slate-200 bg-white text-slate-700 hover:bg-slate-50`

function errorMessage(error: unknown) { return error instanceof Error ? error.message : 'Something went wrong. Please try again.' }
function timestamp(value: string) { return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) }

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${priorityColors[priority]}`}>{priority}</span>
}

export function CategoryBadge({ category }: { category: Category }) {
  return <span className="inline-flex rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-800">{categoryLabels[category]}</span>
}

function TicketDetails({ ticket }: { ticket: Ticket }) {
  return (
    <section aria-label="Ticket details" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 className="text-lg font-semibold text-slate-900">Ticket details</h3>
        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">New</span>
      </div>
      <p className="mt-2 break-all font-mono text-xs text-slate-500">{ticket.id}</p>
      <time dateTime={ticket.created_at} className="mt-1 block text-xs text-slate-500">{timestamp(ticket.created_at)}</time>
      <div className="mt-5 flex flex-wrap gap-2"><CategoryBadge category={ticket.category} /><PriorityBadge priority={ticket.priority} /></div>
      <dl className="mt-6 space-y-5 text-sm">
        <div><dt className="font-semibold text-slate-700">Original message</dt><dd className="mt-1 whitespace-pre-wrap break-words leading-6 text-slate-600" dir="auto">{ticket.message}</dd></div>
        <div><dt className="font-semibold text-slate-700">Order ID</dt><dd className="mt-1 break-all font-mono text-slate-600">{ticket.order_id ?? 'Not provided'}</dd></div>
        <div><dt className="font-semibold text-slate-700">Customer intent</dt><dd className="mt-1 break-words leading-6 text-slate-600" dir="auto">{ticket.customer_intent}</dd></div>
        <div><dt className="font-semibold text-slate-700">Classification reason</dt><dd className="mt-1 break-words leading-6 text-slate-600" dir="auto">{ticket.reason}</dd></div>
      </dl>
      <p className="mt-6 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">Classified by local AI. Review the result before taking action.</p>
    </section>
  )
}

export default function TicketDashboard() {
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [notice, setNotice] = useState('')
  const [page, setPage] = useState<TicketPage | null>(null)
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selected, setSelected] = useState<Ticket | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [detailRevision, setDetailRevision] = useState(0)
  const submitLock = useRef(false)
  const mounted = useRef(true)
  const characterCount = Array.from(message).length

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setListLoading(true)
    setListError('')
    void listTickets(offset, controller.signal).then(result => {
      if (controller.signal.aborted) return
      if (offset > 0 && result.items.length === 0) { setOffset(0); return }
      setPage(result)
    }).catch(error => {
      if (!controller.signal.aborted) setListError(errorMessage(error))
    }).finally(() => { if (!controller.signal.aborted) setListLoading(false) })
    return () => controller.abort()
  }, [offset, revision])

  useEffect(() => {
    if (!selectedId) return
    const controller = new AbortController()
    setDetailLoading(true)
    setDetailError('')
    void getTicket(selectedId, controller.signal).then(ticket => {
      if (!controller.signal.aborted) setSelected(ticket)
    }).catch(error => {
      if (!controller.signal.aborted) setDetailError(errorMessage(error))
    }).finally(() => { if (!controller.signal.aborted) setDetailLoading(false) })
    return () => controller.abort()
  }, [selectedId, detailRevision])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (submitLock.current) return
    setFormError('')
    setNotice('')
    if (!message.trim()) { setFormError('Enter a customer message.'); return }
    if (characterCount > MAX_MESSAGE_LENGTH) { setFormError('Keep the message to 5,000 characters or fewer.'); return }
    submitLock.current = true
    setSubmitting(true)
    try {
      const ticket = await createTicket(message)
      if (!mounted.current) return
      setMessage('')
      setSelected(ticket)
      setSelectedId(ticket.id)
      setOffset(0)
      setRevision(value => value + 1)
      setNotice('Ticket classified and saved. Review its details below.')
    } catch (error) {
      if (mounted.current) setFormError(errorMessage(error))
    } finally {
      submitLock.current = false
      if (mounted.current) setSubmitting(false)
    }
  }

  return (
    <div className="mt-10 space-y-8">
      <section aria-label="Ticket counts" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {([['Total tickets', page?.counts.total], ['New', page?.counts.new], ['High priority', page?.counts.high], ['Urgent', page?.counts.urgent]] as const).map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value ?? '—'}</p>
          </div>
        ))}
      </section>

      <section aria-labelledby="message-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 id="message-heading" className="text-lg font-semibold text-slate-900">Classify a customer message</h2>
        <p className="mt-1 text-sm leading-6 text-slate-500">Paste a message in Greek or English. Local AI identifies the issue and priority, then saves a new ticket.</p>
        <form onSubmit={event => { void submit(event) }} className="mt-5" aria-busy={submitting}>
          <label htmlFor="customer-message" className="block text-sm font-medium text-slate-700">Customer message</label>
          <textarea id="customer-message" name="message" rows={5} value={message} disabled={submitting}
            onChange={event => { setMessage(event.target.value); setFormError(''); setNotice('') }}
            aria-describedby="message-help message-count" aria-invalid={!!formError} dir="auto"
            placeholder="e.g. My order #AB-1234 has not arrived. Can you help?"
            className="mt-2 block w-full resize-y rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:opacity-60" />
          <div className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-slate-500">
            <p id="message-help">Processed on this computer. No customer reply is sent.</p>
            <p id="message-count" className={characterCount > MAX_MESSAGE_LENGTH ? 'text-rose-700' : ''}>{characterCount.toLocaleString()} / 5,000 characters</p>
          </div>
          {formError && <p role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{formError}</p>}
          <div className="mt-5 flex flex-wrap items-center gap-4">
            <button type="submit" disabled={submitting} className={`${button} bg-indigo-600 text-white hover:bg-indigo-700`}>{submitting ? 'Classifying locally…' : 'Classify & save ticket'}</button>
            <p role="status" className="text-sm text-slate-500">{submitting ? 'Loading the model can take a moment. Keep this page open.' : notice}</p>
          </div>
        </form>
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <section aria-labelledby="tickets-heading" className="min-w-0 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-6">
            <div><h2 id="tickets-heading" className="text-lg font-semibold text-slate-900">Tickets</h2><p className="mt-1 text-xs text-slate-500">Newest first · saved on this computer</p></div>
            <button type="button" disabled={listLoading} onClick={() => setRevision(value => value + 1)} className={secondaryButton}>Refresh tickets</button>
          </div>
          {listError && <p role="alert" className="m-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{listError} {page ? 'Showing the last loaded tickets and counts.' : ''}</p>}
          {listLoading && <p role="status" className="p-6 text-sm text-slate-500">Loading tickets…</p>}
          {!listLoading && !listError && page?.items.length === 0 && <p className="p-8 text-center text-sm leading-6 text-slate-500">No tickets yet. Submit a customer message to get started.</p>}
          <ul aria-label="Saved tickets" className="divide-y divide-slate-100">
            {page?.items.map(ticket => (
              <li key={ticket.id}>
                <button type="button" aria-label={`View ticket ${ticket.id}`} aria-pressed={selectedId === ticket.id}
                  onClick={() => { setSelected(null); setSelectedId(ticket.id); setDetailRevision(value => value + 1) }}
                  className={`block w-full p-6 text-left transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-indigo-600 ${selectedId === ticket.id ? 'bg-indigo-50/60' : ''}`}>
                  <div className="flex flex-wrap items-center gap-2"><CategoryBadge category={ticket.category} /><PriorityBadge priority={ticket.priority} /><span className="ml-auto text-xs text-slate-500">New</span></div>
                  <p className="mt-3 line-clamp-2 break-words text-sm font-medium leading-6 text-slate-800" dir="auto">{ticket.customer_intent}</p>
                  <p className="mt-1 line-clamp-2 break-words text-sm leading-6 text-slate-500" dir="auto">{ticket.message}</p>
                  <div className="mt-3 flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span className="break-all font-mono">{ticket.order_id ?? 'No order ID'}</span><time dateTime={ticket.created_at}>{timestamp(ticket.created_at)}</time></div>
                </button>
              </li>
            ))}
          </ul>
          {page && page.counts.total > 0 && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 p-5">
            <p className="text-xs text-slate-500">{page.offset + 1}–{page.offset + page.items.length} of {page.counts.total}</p>
            <div className="flex gap-2"><button type="button" disabled={listLoading || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))} className={secondaryButton}>Previous</button><button type="button" disabled={listLoading || page.offset + page.items.length >= page.counts.total} onClick={() => setOffset(value => value + 20)} className={secondaryButton}>Next</button></div>
          </div>}
        </section>

        <div className="min-w-0 lg:sticky lg:top-6">
          {detailLoading && <p role="status" className="mb-3 text-sm text-slate-500">Loading ticket details…</p>}
          {detailError && <div role="alert" className="mb-3 rounded-lg bg-rose-50 p-4 text-sm text-rose-800">{detailError}<button type="button" onClick={() => setDetailRevision(value => value + 1)} className="ml-3 underline">Retry details</button></div>}
          {selected ? <TicketDetails ticket={selected} /> : !detailLoading && <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-sm leading-6 text-slate-500">Select a ticket to view its original message, customer intent, and classification reason.</div>}
        </div>
      </div>
    </div>
  )
}
