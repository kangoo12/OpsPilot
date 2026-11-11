import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { createReplyDraft, getSupportPolicies, getTicketOrder, getWorkflow, listDrafts, setTicketOrder, type DraftPage, type ReplyDraft, type SupportPolicies, type Ticket, type TicketOrder, type WorkflowState } from './api'
import DraftReviewPanel from './DraftReviewPanel'
import TicketWorkflowPanel, { Activity } from './TicketWorkflowPanel'
import WorkspaceTabs, { type WorkspaceTab } from './WorkspaceTabs'

const button = 'rounded-lg px-3 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-50'
const panel = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6'
const eligibility = { review_available: 'Available for review — not an approval', not_eligible: 'Not eligible under the demo record', not_started: 'Review period not started', unknown: 'Not verified' }
function errorText(error: unknown) { return error instanceof Error ? error.message : 'The request failed. Please try again.' }
function date(value: string) { return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { dateStyle: 'medium' }) }

export default function TicketSupport({ ticket, onOrderChanged, overview, workspace = false }: { ticket: Ticket; onOrderChanged?: () => void; overview?: ReactNode; workspace?: boolean }) {
  const [tab, setTab] = useState<WorkspaceTab>('overview')
  const [order, setOrder] = useState<TicketOrder | null>(null)
  const [reference, setReference] = useState('')
  const [orderLoading, setOrderLoading] = useState(true)
  const [orderError, setOrderError] = useState('')
  const [saving, setSaving] = useState(false)
  const [drafts, setDrafts] = useState<DraftPage>({ items: [], total: 0 })
  const [draftId, setDraftId] = useState('')
  const [draftLoading, setDraftLoading] = useState(true)
  const [draftError, setDraftError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [policies, setPolicies] = useState<SupportPolicies | null>(null)
  const [policiesError, setPoliciesError] = useState('')
  const [revision, setRevision] = useState(0)
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null)
  const [workflowLoading, setWorkflowLoading] = useState(true)
  const [workflowError, setWorkflowError] = useState('')
  const [actionRevision, setActionRevision] = useState(0)
  const [reviewDirty, setReviewDirty] = useState(false)
  const [reviewNotice, setReviewNotice] = useState('')
  const mounted = useRef(true)
  const actionLock = useRef(false)
  const selectedDraft = drafts.items.find(draft => draft.id === draftId) ?? drafts.items[0]
  const outdated = selectedDraft && order && JSON.stringify(selectedDraft.order_context) !== JSON.stringify(order)
  const referenceDirty = !!order && reference.trim().replace(/^#/, '').toUpperCase() !== (order.reference_order_id ?? '').toUpperCase()
  const discrepancy = order?.consistency?.status === 'discrepancy'
  const unsafeHistorical = selectedDraft && (discrepancy || selectedDraft.snapshot_consistency?.status === 'discrepancy') && selectedDraft.order_context.consistency?.status !== 'discrepancy'

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setWorkflowLoading(true); setWorkflowError('')
    void getWorkflow(ticket.id, controller.signal).then(result => { if (!controller.signal.aborted) setWorkflow(result) })
      .catch(() => { if (!controller.signal.aborted) setWorkflowError('Cannot load human review state. Refresh before reviewing drafts.') })
      .finally(() => { if (!controller.signal.aborted) setWorkflowLoading(false) })
    return () => controller.abort()
  }, [ticket.id, revision, actionRevision])

  useEffect(() => {
    const controller = new AbortController()
    setOrderLoading(true); setDraftLoading(true); setOrderError(''); setDraftError(''); setPoliciesError('')
    void getTicketOrder(ticket.id, controller.signal).then(result => {
      if (!controller.signal.aborted) { setOrder(result); setReference(result.reference_order_id ?? '') }
    }).catch(error => { if (!controller.signal.aborted) setOrderError(errorText(error)) })
      .finally(() => { if (!controller.signal.aborted) setOrderLoading(false) })
    void listDrafts(ticket.id, controller.signal).then(result => {
      if (!controller.signal.aborted) { setDrafts(result); setDraftId(current => result.items.some(item => item.id === current) ? current : result.items[0]?.id ?? '') }
    }).catch(error => { if (!controller.signal.aborted) setDraftError(errorText(error)) })
      .finally(() => { if (!controller.signal.aborted) setDraftLoading(false) })
    void getSupportPolicies(controller.signal).then(result => { if (!controller.signal.aborted) setPolicies(result) })
      .catch(() => { if (!controller.signal.aborted) setPoliciesError('Policy details could not be loaded. Refresh to try again.') })
    return () => controller.abort()
  }, [ticket.id, revision])

  async function correctOrder(event: FormEvent) {
    event.preventDefault()
    if (actionLock.current) return
    const value = reference.trim().replace(/^#/, '')
    if (value && !/^[\p{L}\p{N}_][\p{L}\p{N}_/-]{0,63}$/u.test(value)) { setOrderError('Enter a valid order ID of up to 64 characters.'); return }
    actionLock.current = true; setSaving(true); setOrderError('')
    try {
      const result = order?.context_fingerprint ? await setTicketOrder(ticket.id, value || null, order.context_fingerprint) : await setTicketOrder(ticket.id, value || null)
      if (mounted.current) { setOrder(result); setReference(result.reference_order_id ?? ''); setActionRevision(value => value + 1); onOrderChanged?.() }
    } catch (error) { if (mounted.current) setOrderError(errorText(error)) }
    finally { actionLock.current = false; if (mounted.current) setSaving(false) }
  }

  function reviewed(result: ReplyDraft) {
    setDrafts(current => ({ items: current.items.some(item => item.id === result.id) ? current.items.map(item => item.id === result.id ? result : item) : [result, ...current.items].slice(0, 20), total: current.total + (current.items.some(item => item.id === result.id) ? 0 : 1) }))
    setDraftId(result.id); setReviewDirty(false); setActionRevision(value => value + 1); onOrderChanged?.()
    setReviewNotice(result.status === 'approved' ? 'Draft approved. Nothing was sent; ticket status is unchanged.' : result.status === 'rejected' ? 'Draft rejected. The reason is recorded.' : 'Pending draft saved. Previous content is preserved in its revision history.')
  }

  function refresh() {
    if (reviewDirty && !window.confirm('Discard unsaved reply edits and reload this ticket?')) return
    setRevision(value => value + 1)
  }

  async function generate() {
    if (actionLock.current) return
    actionLock.current = true; setGenerating(true); setDraftError('')
    try {
      const draft = await createReplyDraft(ticket.id)
      if (mounted.current) {
        setDrafts(current => ({ items: [draft, ...current.items].slice(0, 20), total: current.total + 1 }))
        setDraftId(draft.id)
      }
    } catch (error) { if (mounted.current) setDraftError(errorText(error)) }
    finally { actionLock.current = false; if (mounted.current) setGenerating(false) }
  }

  return (
    <div className="space-y-4">
      {workspace && <WorkspaceTabs active={tab} onChange={setTab} idPrefix={`workspace-${ticket.id}`} />}
      {workspace && !order?.consistency?.requires_human_review && (ticket.requires_human_review || workflow?.consistency.requires_human_review) && <p role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">Human Review Required. Verify the order details before approving a reply.</p>}
      {workspace && unsafeHistorical && <p role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">Selected historical draft contains conflicting order facts. Do not use without review.</p>}
      {workspace && (orderError || workflowError) && <p role="alert" className="text-sm text-rose-800">{orderError || workflowError}</p>}
      {order?.consistency?.requires_human_review && <aside role="alert" aria-label="Order consistency warning" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        <p className="font-semibold">{discrepancy ? 'Order discrepancy — human review required' : 'Order verification — human review required'}</p>
        <ul className="mt-2 list-disc space-y-2 pl-4 text-xs leading-5">{order.consistency.issues.map(issue => <li key={issue.code}>
          {issue.message}{issue.customer_reported && <span className="block">Customer reports: {issue.customer_reported}</span>}
          {issue.order_recorded && <span className="block">Order record: {issue.order_recorded}</span>}
        </li>)}</ul>
        {discrepancy && <p className="mt-2 text-xs leading-5">Neither source has been reconciled. Suggested replies will ask for clarification and omit disputed order facts. No explanation or correction has been assumed.</p>}
      </aside>}
      <div id={`workspace-${ticket.id}-overview-panel`} aria-labelledby={workspace ? `workspace-${ticket.id}-overview` : undefined} hidden={workspace && tab !== 'overview'} role={workspace ? 'tabpanel' : undefined} aria-label={workspace ? 'Overview' : undefined} className="space-y-4">
        {overview}
        <TicketWorkflowPanel ticketId={ticket.id} state={workflow} loading={workflowLoading} error={workflowError} revision={actionRevision + revision} showActivity={!workspace}
          onChanged={() => { setRevision(value => value + 1); setActionRevision(value => value + 1); onOrderChanged?.() }} />
      </div>
      <div className="flex justify-end"><button type="button" disabled={generating || saving || orderLoading || draftLoading}
        className={`${button} text-indigo-700 hover:bg-indigo-50`} onClick={refresh}>Refresh order & drafts</button></div>
      <section id={`workspace-${ticket.id}-order-panel`} aria-labelledby={workspace ? `workspace-${ticket.id}-order` : undefined} hidden={workspace && tab !== 'order'} role={workspace ? 'tabpanel' : undefined} aria-label="Order details" className={panel}>
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-base font-semibold text-slate-900">Order Details</h3><span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">Fictional demo data</span></div>
        {orderLoading && <p role="status" className="mt-3 text-sm text-slate-500">Looking up verified order details…</p>}
        {orderError && <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{orderError}</p>}
        {!orderLoading && order && <div className="mt-4">
          {order.consistency?.status === 'consistent' && <p className="mb-2 text-xs text-slate-500">No material discrepancy detected in recognized product and delivery statements.</p>}
          {order.lookup_status === 'found' && order.order ? <>
            <p className="text-sm font-semibold text-emerald-800">Found in demo records · #{order.order.id}</p>
            <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div className="sm:col-span-2"><dt className="text-xs text-slate-500">Product</dt><dd className="mt-1 break-words text-slate-800">{order.order.product}</dd></div>
              <div><dt className="text-xs text-slate-500">Order date</dt><dd className="mt-1 text-slate-700">{date(order.order.order_date)}</dd></div>
              <div><dt className="text-xs text-slate-500">Delivery status</dt><dd className="mt-1 capitalize text-slate-700">{order.order.delivery_status.replaceAll('_', ' ')}</dd></div>
              <div className="sm:col-span-2"><dt className="text-xs text-slate-500">Estimated delivery</dt><dd className="mt-1 text-slate-700">{order.order.estimated_delivery_date ? `${date(order.order.estimated_delivery_date)} · estimate, not a guarantee` : 'Not available in verified records'}</dd></div>
              <div><dt className="text-xs text-slate-500">Returns</dt><dd className="mt-1 text-slate-700">{eligibility[order.order.return_eligibility]}</dd></div>
              <div><dt className="text-xs text-slate-500">Warranty support</dt><dd className="mt-1 text-slate-700">{eligibility[order.order.warranty_eligibility]}</dd></div>
            </dl>
            <p className="mt-3 text-xs text-slate-500">Demo snapshot: {date(order.order.snapshot_date)}. This is not live carrier tracking.</p>
          </> : <p className="rounded-lg bg-amber-50 p-3 text-sm leading-6 text-amber-900">{order.lookup_status === 'unknown' ? `Unknown order: ${order.reference_order_id}. No verified order information was found.` : 'No order ID provided. Add a reference below if available.'}</p>}
          <p className="mt-3 text-xs text-slate-500">Original extracted ID: <span className="font-mono">{order.extracted_order_id ?? 'None'}</span> · Using {order.source === 'manual' ? 'manual reference' : 'extracted reference'}</p>
        </div>}
        <form onSubmit={event => { void correctOrder(event) }} className="mt-4">
          <label htmlFor={`order-${ticket.id}`} className="text-sm font-medium text-slate-700">Order ID for lookup</label>
          <div className="mt-2 flex flex-wrap gap-2"><input id={`order-${ticket.id}`} value={reference} maxLength={65} disabled={generating || saving || orderLoading || reviewDirty}
            onChange={event => setReference(event.target.value)} placeholder="e.g. 7821 or GR-1042"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:opacity-60" />
            <button type="submit" disabled={generating || saving || orderLoading || reviewDirty} className={`${button} border border-slate-200 text-slate-700 hover:bg-slate-50`}>{saving ? 'Looking up…' : 'Save & lookup'}</button></div>
          <p className="mt-2 text-xs leading-5 text-slate-500">A correction is saved for this ticket. The original extraction stays unchanged. Clear the field to use no order reference.</p>
        </form>
      </section>
      <section id={`workspace-${ticket.id}-reply-panel`} aria-labelledby={workspace ? `workspace-${ticket.id}-reply` : undefined} hidden={workspace && tab !== 'reply'} role={workspace ? 'tabpanel' : undefined} aria-label="AI suggested reply" className={panel}>
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-base font-semibold text-slate-900">AI Suggested Reply</h3><span className={`rounded-full px-2 py-1 text-xs font-semibold ${selectedDraft?.status === 'approved' ? 'bg-emerald-50 text-emerald-800' : selectedDraft?.status === 'rejected' ? 'bg-rose-50 text-rose-800' : 'bg-amber-50 text-amber-900'}`}>{selectedDraft?.status === 'approved' ? 'Approved' : selectedDraft?.status === 'rejected' ? 'Rejected' : 'Pending human review'}</span></div>
        <p className="mt-2 text-xs leading-5 text-slate-500">Review every draft before approval. Approving never sends a message or resolves the ticket.</p>
        <button type="button" disabled={generating || saving || orderLoading || draftLoading || !order || !!orderError || !!draftError || referenceDirty || reviewDirty}
          onClick={() => { void generate() }} className={`${button} mt-4 bg-indigo-600 text-white hover:bg-indigo-700`}>{generating ? 'Generating locally…' : 'Generate suggested reply'}</button>
        {referenceDirty && <p className="mt-2 text-xs text-amber-800">Save the order reference before generating a draft.</p>}
        {generating && <p role="status" className="mt-3 text-sm text-slate-500">Preparing a grounded draft with local Qwen. Keep this ticket open.</p>}
        {draftLoading && <p role="status" className="mt-3 text-sm text-slate-500">Loading saved drafts…</p>}
        {draftError && <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{draftError} Use “Refresh order & drafts” before retrying.</p>}
        {drafts.items.length > 1 && <div className="mt-4"><label htmlFor={`draft-${ticket.id}`} className="text-xs font-medium text-slate-500">Saved drafts</label>
          <select id={`draft-${ticket.id}`} disabled={reviewDirty} value={selectedDraft?.id ?? ''} onChange={event => { setDraftId(event.target.value); setReviewNotice('') }} className="mt-1 block w-full rounded-lg border border-slate-200 bg-white p-2 text-sm">
            {drafts.items.map(draft => <option key={draft.id} value={draft.id}>{new Date(draft.created_at).toLocaleString()} · {draft.status.replaceAll('_', ' ')} · {draft.language === 'el' ? 'Greek' : 'English'}</option>)}
          </select></div>}
        {drafts.total > 20 && <p className="mt-2 text-xs text-slate-500">Showing the latest 20 of {drafts.total} saved drafts.</p>}
        {selectedDraft ? <>
          {outdated && <p role="status" className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">The order reference or verified facts have changed since this draft. Generate a new draft using the current details.</p>}
          <p className="mt-4 text-xs text-slate-500">Based on {selectedDraft.order_context.reference_order_id ? `order reference #${selectedDraft.order_context.reference_order_id}` : 'no order reference'} · {new Date(selectedDraft.created_at).toLocaleString()}</p>
          {unsafeHistorical ? <details className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
            <summary className="cursor-pointer font-semibold">Historical draft — conflicting order facts, do not use without review</summary>
            <p className="mt-2 text-xs">Preserved unchanged for history. This draft predates the current discrepancy check.</p>
            <div data-testid="historical-reply-text" dir="auto" className="mt-3 whitespace-pre-wrap break-words leading-7">{selectedDraft.reply_text}</div>
          </details> : <div data-testid="reply-text" dir="auto" className="mt-3 whitespace-pre-wrap break-words rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 text-sm leading-7 text-slate-800">{selectedDraft.reply_text}</div>}
          <p className="mt-3 text-xs text-slate-500">{selectedDraft.model} · {selectedDraft.policy_version}{selectedDraft.origin === 'human_revision' ? ' · Human revision' : ''}</p>
          <DraftReviewPanel key={`${selectedDraft.id}:${selectedDraft.version ?? 1}`} ticketId={ticket.id} draft={selectedDraft} workflow={workflowLoading || workflowError ? null : workflow} onChanged={reviewed} onDirtyChange={setReviewDirty} />
        </> : !draftLoading && !generating && <p className="mt-4 text-sm text-slate-500">No saved reply draft yet.</p>}
        {reviewNotice && <p role="status" className="mt-3 text-sm font-medium text-emerald-800">{reviewNotice}</p>}
        {policiesError && <p role="alert" className="mt-3 text-xs text-amber-900">{policiesError}</p>}
        {policies && <details className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500"><summary className="cursor-pointer font-medium">Fictional company policies</summary><ul className="mt-2 list-disc space-y-2 pl-4 leading-5">{policies.policies.map(policy => <li key={policy}>{policy}</li>)}</ul></details>}
      </section>
      {workspace && <section id={`workspace-${ticket.id}-activity-panel`} aria-labelledby={`workspace-${ticket.id}-activity`} hidden={tab !== 'activity'} role="tabpanel" aria-label="Activity History" className={panel}>
        {tab === 'activity' && <Activity ticketId={ticket.id} revision={actionRevision + revision} expanded />}
      </section>}
    </div>
  )
}
