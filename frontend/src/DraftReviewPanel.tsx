import { useEffect, useRef, useState } from 'react'
import { editReplyDraft, getDraftRevisions, reviewReplyDraft, type DraftRevision, type ReplyDraft, type WorkflowState } from './api'
import ConfirmDialog from './ConfirmDialog'

const button = 'rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600'

export default function DraftReviewPanel({ ticketId, draft, workflow, onChanged, onDirtyChange }: {
  ticketId: string; draft: ReplyDraft; workflow: WorkflowState | null; onChanged: (draft: ReplyDraft) => void; onDirtyChange: (dirty: boolean) => void
}) {
  const [editing, setEditing] = useState(false)
  const [content, setContent] = useState(draft.reply_text)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [dialog, setDialog] = useState<'approve' | 'reject' | 'regenerate' | null>(null)
  const [reason, setReason] = useState('')
  const [historyOpen, setHistoryOpen] = useState(false)
  const [history, setHistory] = useState<DraftRevision[]>([])
  const [historyError, setHistoryError] = useState('')
  const mounted = useRef(true)
  const lock = useRef(false)
  const dirty = content !== draft.reply_text
  const decided = draft.status !== 'pending_review'
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; onDirtyChange(false) } }, [])
  useEffect(() => { onDirtyChange(editing && dirty) }, [editing, dirty])
  useEffect(() => {
    if (!historyOpen) return
    const controller = new AbortController()
    setHistoryError('')
    void getDraftRevisions(ticketId, draft.id, controller.signal).then(items => { if (!controller.signal.aborted) setHistory(items) })
      .catch(() => { if (!controller.signal.aborted) setHistoryError('Could not load revision history. Close and reopen to retry.') })
    return () => controller.abort()
  }, [historyOpen, draft.id, draft.version, ticketId])

  async function save() {
    if (!workflow || lock.current) return
    if (!content.trim() || Array.from(content).length > 4000) { setError('Enter a reply between 1 and 4,000 characters.'); return }
    lock.current = true; setBusy(true); setError(''); setNotice('')
    try {
      const result = await editReplyDraft(ticketId, draft, content, workflow.context_fingerprint)
      if (mounted.current) { setEditing(false); onDirtyChange(false); onChanged(result); setNotice('Saved as a pending draft. Nothing was sent.') }
    } catch (error) { if (mounted.current) setError(error instanceof Error ? error.message : 'Could not save the draft.') }
    finally { lock.current = false; if (mounted.current) setBusy(false) }
  }

  async function decide() {
    if (!workflow || !dialog || lock.current) return
    if (dialog === 'reject' && reason.trim().length < 5) { setError('Enter a rejection reason of at least 5 characters.'); return }
    lock.current = true; setBusy(true); setError(''); setNotice('')
    const action = dialog
    try {
      const result = await reviewReplyDraft(ticketId, draft, action, workflow.context_fingerprint, reason.trim())
      if (mounted.current) {
        setDialog(null); onChanged(result)
        setNotice(action === 'approve' ? 'Draft approved. Nothing was sent and ticket status is unchanged.' : action === 'reject' ? 'Draft rejected. The reason is recorded.' : 'New AI draft saved. The previous draft is preserved.')
      }
    } catch (error) { if (mounted.current) { setDialog(null); setError(error instanceof Error ? error.message : 'The action failed. Refresh before retrying.') } }
    finally { lock.current = false; if (mounted.current) setBusy(false) }
  }

  return <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
    <p className="text-xs text-slate-500">Revision {draft.version ?? 1}{draft.reviewer ? ` · ${draft.reviewer}` : ' · Not yet reviewed'}{draft.updated_at ? ` · Modified ${new Date(draft.updated_at).toLocaleString()}` : ''}</p>
    {draft.approved_at && <p className="text-xs font-medium text-emerald-800">Approved {new Date(draft.approved_at).toLocaleString()}. Approved content is immutable; editing creates a new pending draft.</p>}
    {draft.rejection_reason && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">Rejected: {draft.rejection_reason}</p>}
    {draft.parent_draft_id && <p className="break-all text-xs text-slate-500">Based on draft {draft.parent_draft_id}</p>}
    {editing ? <div className="space-y-2">
      <label htmlFor="reply-draft-editor" className="text-sm font-medium text-slate-700">Reply draft content</label>
      <textarea id="reply-draft-editor" rows={7} value={content} disabled={busy} onChange={event => { setContent(event.target.value); setError('') }} dir="auto"
        className="block w-full rounded-xl border border-indigo-200 px-3 py-2 text-sm leading-6 text-slate-800 outline-none focus:ring-2 focus:ring-indigo-100" />
      <p className="text-xs text-slate-500">{Array.from(content).length.toLocaleString()} / 4,000 characters. {decided ? 'A new pending revision will preserve this reviewed draft.' : 'Saving records a revision; it does not approve or send the reply.'}</p>
      <div className="flex flex-wrap gap-2"><button type="button" disabled={busy || !dirty || !workflow} onClick={() => { void save() }} className={`${button} border-indigo-200 text-indigo-700`}>{busy ? 'Saving…' : decided ? 'Save as pending revision' : 'Save Draft'}</button>
        <button type="button" disabled={busy} onClick={() => { setEditing(false); setContent(draft.reply_text); onDirtyChange(false); setError('') }} className={button}>Discard edits</button></div>
    </div> : <div className="flex flex-wrap gap-2">
      <button type="button" disabled={busy || !workflow} onClick={() => { setEditing(true); setError(''); setNotice('') }} className={button}>{decided ? 'Create pending revision' : 'Edit reply'}</button>
      <button type="button" disabled={busy || !workflow || decided || !!draft.approval_blockers?.length} onClick={() => { setDialog('approve'); setError('') }} className={`${button} border-emerald-200 text-emerald-800`}>Approve</button>
      <button type="button" disabled={busy || !workflow || decided} onClick={() => { setDialog('reject'); setReason(''); setError('') }} className={`${button} text-rose-700`}>Reject</button>
      <button type="button" disabled={busy || !workflow} onClick={() => { setDialog('regenerate'); setError('') }} className={button}>Regenerate</button>
    </div>}
    {!decided && !!draft.approval_blockers?.length && <div className="rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-900"><p className="font-semibold">Before approval</p><ul className="mt-1 list-disc pl-4">{draft.approval_blockers.map(item => <li key={item}>{item}</li>)}</ul></div>}
    {error && !dialog && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    {notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    <details onToggle={event => setHistoryOpen(event.currentTarget.open)} className="text-xs text-slate-500"><summary className="cursor-pointer font-medium">Draft revision history</summary>
      {historyError && <p role="alert" className="mt-2 text-rose-700">{historyError}</p>}
      {historyOpen && !history.length && !historyError && <p className="mt-2">Loading revisions…</p>}
      <ol className="mt-3 space-y-3">{history.map(item => <li key={item.version} className="rounded-lg border border-slate-100 p-3"><p className="font-medium text-slate-700">Revision {item.version} · {item.action} · {item.actor}</p><time>{new Date(item.created_at).toLocaleString()}</time>{item.reason && <p className="mt-1">{item.reason}</p>}<pre dir="auto" className="mt-2 whitespace-pre-wrap break-words font-sans leading-5">{item.content}</pre></li>)}</ol>
    </details>
    {draft.original_content && draft.original_content !== draft.reply_text && <details className="text-xs text-slate-500"><summary className="cursor-pointer font-medium">Original draft content</summary><p dir="auto" className="mt-2 whitespace-pre-wrap break-words leading-5">{draft.original_content}</p></details>}
    {dialog && <ConfirmDialog title={dialog === 'approve' ? 'Approve this draft?' : dialog === 'reject' ? 'Reject this draft?' : 'Regenerate a new draft?'}
      confirmLabel={dialog === 'approve' ? 'Confirm approval' : dialog === 'reject' ? 'Confirm rejection' : 'Confirm regeneration'} busy={busy} onCancel={() => { setDialog(null); setError('') }} onConfirm={() => { void decide() }}>
      <p>{dialog === 'approve' ? 'Approve only the displayed saved revision after reviewing its facts. Approval sends nothing and does not resolve the ticket.' : dialog === 'reject' ? 'The draft and its history will be preserved. Explain why this reply should not be used.' : 'Local Qwen will create a separate pending draft. Existing content and review decisions will be preserved.'}</p>
      {dialog === 'reject' && <><label htmlFor="rejection-reason" className="block font-medium text-slate-700">Rejection reason</label><textarea id="rejection-reason" rows={3} maxLength={1000} disabled={busy} value={reason} onChange={event => setReason(event.target.value)} className="w-full rounded-lg border border-slate-300 p-2" />{error && <p role="alert" className="text-rose-700">{error}</p>}</>}
    </ConfirmDialog>}
  </div>
}
