import { useEffect, useState } from 'react'
import { documentDiscrepancy, getActivity, statusLabels, updateTicketStatus, type ActivityEvent, type TicketStatus, type WorkflowState } from './api'
import ConfirmDialog from './ConfirmDialog'

const button = 'rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50'
const eventLabels: Record<string, string> = {
  ticket_created: 'Ticket created', ticket_status_changed: 'Ticket status changed', order_reference_corrected: 'Order reference corrected',
  order_reference_imported: 'Historical order reference imported', draft_generated: 'AI draft generated', draft_edited: 'Draft edited',
  draft_approved: 'Draft approved — nothing sent', draft_rejected: 'Draft rejected', draft_regenerated: 'AI draft regenerated',
  draft_revision_created: 'Pending revision created', discrepancy_documented: 'Human discrepancy review documented',
}

function Activity({ ticketId, revision }: { ticketId: string; revision: number }) {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<ActivityEvent[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  useEffect(() => { setOffset(0) }, [revision])
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    setLoading(true); setError('')
    void getActivity(ticketId, offset, controller.signal).then(page => {
      if (!controller.signal.aborted) { setItems(page.items); setTotal(page.total) }
    }).catch(() => { if (!controller.signal.aborted) setError('Could not load activity. Close and reopen to retry.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [ticketId, revision, open, offset])
  return <details onToggle={event => setOpen(event.currentTarget.open)} className="mt-4 border-t border-slate-100 pt-3 text-sm">
    <summary className="cursor-pointer font-medium text-slate-700">Activity History</summary>
    {loading && <p role="status" className="mt-3 text-xs text-slate-500">Loading activity…</p>}
    {error && <p role="alert" className="mt-3 text-xs text-rose-700">{error}</p>}
    {!loading && !error && !items.length && open && <p className="mt-3 text-xs text-slate-500">No recorded activity yet.</p>}
    <ol className="mt-3 space-y-3 border-l border-indigo-100 pl-4">{items.map(item => <li key={item.id} className="text-xs leading-5 text-slate-500">
      <p className="font-semibold text-slate-700">{eventLabels[item.event_type] ?? item.event_type.replaceAll('_', ' ')}</p>
      <p>{item.actor} · {new Date(item.created_at).toLocaleString()}</p>
      {'previous' in item.data && 'new' in item.data && <p>{String(item.data.previous ?? 'None').replaceAll('_', ' ')} → {String(item.data.new ?? 'None').replaceAll('_', ' ')}</p>}
      {typeof item.data.reason === 'string' && <p className="mt-1 break-words text-slate-600">{item.data.reason}</p>}
      {typeof item.data.draft_id === 'string' && <p className="break-all font-mono">Draft {item.data.draft_id}</p>}
      {item.data.historical_import === true && <p>Imported original timestamp; no historical human action is inferred.</p>}
      {item.data.original_change_time_unknown === true && <p>Imported reference. Its original change time was not recorded.</p>}
    </li>)}</ol>
    {total > 30 && <div className="mt-3 flex gap-2"><button className={button} disabled={loading || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 30))}>Newer</button><button className={button} disabled={loading || offset + items.length >= total} onClick={() => setOffset(value => value + 30)}>Older</button></div>}
  </details>
}

export default function TicketWorkflowPanel({ ticketId, state, loading, error, revision, onChanged }: {
  ticketId: string; state: WorkflowState | null; loading: boolean; error: string; revision: number; onChanged: () => void
}) {
  const [target, setTarget] = useState<TicketStatus>('new')
  const [dialog, setDialog] = useState<'status' | 'resolution' | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => { if (state) setTarget(state.status) }, [state?.status, state?.version])
  async function confirm() {
    if (!state || busy || !dialog) return
    if (dialog === 'resolution' && reason.trim().length < 10) { setActionError('Record a review reason of at least 10 characters.'); return }
    setBusy(true); setActionError(''); setNotice('')
    const action = dialog
    try {
      if (action === 'status') await updateTicketStatus(ticketId, target, state.version)
      else await documentDiscrepancy(ticketId, state.context_fingerprint, reason.trim())
      setDialog(null)
      setNotice(action === 'status' ? 'Ticket status updated.' : 'Human review documented for the current context. Warnings and draft safety checks remain active.')
      onChanged()
    } catch (error) { setDialog(null); setActionError(error instanceof Error ? error.message : 'The change failed. Refresh before retrying.') }
    finally { setBusy(false) }
  }
  return <section aria-label="Ticket workflow" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
    <h3 className="text-base font-semibold text-slate-900">Ticket workflow</h3>
    <p className="mt-1 text-xs text-slate-500">Local Operator · demo identity, no authentication</p>
    {loading && <p role="status" className="mt-3 text-sm text-slate-500">Loading review state…</p>}
    {error && <p role="alert" className="mt-3 text-sm text-rose-700">{error}</p>}
    {state && <>
      <label htmlFor="ticket-status" className="mt-4 block text-sm font-medium text-slate-700">Ticket status</label>
      <div className="mt-2 flex flex-wrap gap-2"><select id="ticket-status" value={target} disabled={busy || loading} onChange={event => setTarget(event.target.value as TicketStatus)} className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white p-2 text-sm">
        {[state.status, ...state.allowed_transitions].map(status => <option key={status} value={status}>{statusLabels[status]}</option>)}
      </select><button type="button" disabled={busy || loading || target === state.status} className={button} onClick={() => { setDialog('status'); setActionError('') }}>{state.status === 'resolved' ? 'Reopen ticket' : 'Update status'}</button></div>
      {state.consistency.requires_human_review && <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
        <p className="font-semibold">Human Review Required</p>
        {state.resolution ? <><p className="mt-1">Documented by {state.resolution.actor} · {new Date(state.resolution.created_at).toLocaleString()}</p><p className="mt-2 break-words">{state.resolution.reason}</p><p className="mt-2">This documentation does not change the customer message or order record. Unsupported reply claims remain blocked.</p></>
          : <><p className="mt-1">Correct the order reference below if appropriate, or explicitly document your review. Do not assume which conflicting source is correct.</p><button type="button" disabled={busy || loading} className={`${button} mt-3 bg-white`} onClick={() => { setDialog('resolution'); setReason(''); setActionError('') }}>Document human review</button></>}
      </div>}
    </>}
    {actionError && !dialog && <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{actionError}</p>}
    {notice && <p role="status" className="mt-3 text-sm text-emerald-800">{notice}</p>}
    <Activity ticketId={ticketId} revision={revision} />
    {dialog && state && <ConfirmDialog title={dialog === 'status' ? 'Confirm ticket status change' : 'Document human discrepancy review'} busy={busy}
      confirmLabel={dialog === 'status' ? 'Confirm status change' : 'Confirm documentation'} onCancel={() => { setDialog(null); setActionError('') }} onConfirm={() => { void confirm() }}>
      {dialog === 'status' ? <p>Change from {statusLabels[state.status]} to {statusLabels[target]}? This does not send a message or change any draft review decision.</p> : <>
        <p>Record what you reviewed and how the discrepancy should be handled. This applies only to the current order context. It does not verify disputed facts or approve a draft.</p>
        <label htmlFor="resolution-reason" className="block font-medium text-slate-700">Human review reason</label>
        <textarea id="resolution-reason" rows={4} maxLength={1000} disabled={busy} value={reason} onChange={event => setReason(event.target.value)} className="w-full rounded-lg border border-slate-300 p-2" />
        {actionError && <p role="alert" className="text-rose-700">{actionError}</p>}
      </>}
    </ConfirmDialog>}
  </section>
}
