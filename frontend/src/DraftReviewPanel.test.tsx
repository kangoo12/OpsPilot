// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import DraftReviewPanel from './DraftReviewPanel'
import { editReplyDraft, getDraftRevisions, reviewReplyDraft, type ReplyDraft, type WorkflowState } from './api'

vi.mock('./api', async () => ({ ...await vi.importActual<typeof import('./api')>('./api'), editReplyDraft: vi.fn(), getDraftRevisions: vi.fn(), reviewReplyDraft: vi.fn() }))
const context = { reference_order_id: null, extracted_order_id: null, source: 'extracted' as const, lookup_status: 'not_provided' as const, order: null }
const draft: ReplyDraft = { id: 'draft-1', ticket_id: 'ticket-1', reply_text: 'Please confirm the order reference.', language: 'en', status: 'pending_review', model: 'qwen3.5:9b', order_context: context, policy_version: 'v2', created_at: '2026-11-10T20:00:00Z', version: 1, original_content: 'Please confirm the order reference.', approval_blockers: [] }
const workflow: WorkflowState = { status: 'new', version: 1, allowed_transitions: ['in_progress'], context_fingerprint: 'a'.repeat(64), consistency: { status: 'consistent', requires_human_review: false, issues: [], reported_products: [], reported_delivery_states: [], check_version: 'v1' }, operator: 'Local Operator', identity_is_authenticated: false, resolution: null }
const changed = vi.fn(), dirty = vi.fn()
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(editReplyDraft).mockResolvedValue({ ...draft, reply_text: 'An edited draft.', version: 2 })
  vi.mocked(reviewReplyDraft).mockResolvedValue({ ...draft, status: 'approved', version: 2 })
  vi.mocked(getDraftRevisions).mockResolvedValue([{ draft_id: draft.id, version: 1, content: draft.reply_text, status: 'pending_review', actor: 'Local AI', action: 'created', reason: null, created_at: draft.created_at }])
})
afterEach(cleanup)
function show(value = draft, state: WorkflowState | null = workflow) {
  render(<DraftReviewPanel ticketId={value.ticket_id} draft={value} workflow={state} onChanged={changed} onDirtyChange={dirty} />)
}

describe('human draft review', () => {
  it('edits and saves the pending revision with a version and order context', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: 'Edit reply' }))
    fireEvent.change(screen.getByLabelText('Reply draft content'), { target: { value: 'An edited draft.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }))
    await waitFor(() => expect(changed).toHaveBeenCalled())
    expect(editReplyDraft).toHaveBeenCalledWith('ticket-1', draft, 'An edited draft.', workflow.context_fingerprint)
  })

  it('requires confirmation before approval and sends no action on cancel', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(screen.getByRole('dialog').textContent).toContain('Approval sends nothing')
    expect(reviewReplyDraft).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(reviewReplyDraft).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm approval' }))
    await waitFor(() => expect(changed).toHaveBeenCalled())
    expect(reviewReplyDraft).toHaveBeenCalledWith('ticket-1', draft, 'approve', workflow.context_fingerprint, '')
  })

  it('requires a rejection reason before sending the request', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }))
    expect(reviewReplyDraft).not.toHaveBeenCalled()
    expect(screen.getAllByRole('alert').some(node => node.textContent?.includes('rejection reason'))).toBe(true)
    fireEvent.change(screen.getByLabelText('Rejection reason'), { target: { value: 'The reply needs clarification.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }))
    await waitFor(() => expect(reviewReplyDraft).toHaveBeenCalledWith('ticket-1', draft, 'reject', workflow.context_fingerprint, 'The reply needs clarification.'))
  })

  it('regenerates into a separate draft after confirmation', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }))
    expect(screen.getByRole('dialog').textContent).toContain('separate pending draft')
    fireEvent.click(screen.getByRole('button', { name: 'Confirm regeneration' }))
    await waitFor(() => expect(reviewReplyDraft).toHaveBeenCalledWith('ticket-1', draft, 'regenerate', workflow.context_fingerprint, ''))
  })

  it('offers a new pending revision for approved content', async () => {
    show({ ...draft, status: 'approved', approved_at: '2026-11-10T20:01:00Z', version: 2 })
    expect((screen.getByRole('button', { name: 'Approve' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Create pending revision' }))
    fireEvent.change(screen.getByLabelText('Reply draft content'), { target: { value: 'New content for a pending child.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save as pending revision' }))
    await waitFor(() => expect(editReplyDraft).toHaveBeenCalledWith('ticket-1', expect.objectContaining({ status: 'approved', version: 2 }), 'New content for a pending child.', workflow.context_fingerprint))
  })

  it('blocks direct approval when the backend reports a discrepancy blocker', () => {
    show({ ...draft, approval_blockers: ['Document the current discrepancy before approval.'] })
    expect((screen.getByRole('button', { name: 'Approve' }) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('Document the current discrepancy before approval.')).toBeTruthy()
  })

  it('retains unsaved content after a stale update error', async () => {
    vi.mocked(editReplyDraft).mockRejectedValue(new Error('This record changed. Refresh before applying your changes.'))
    show()
    fireEvent.click(screen.getByRole('button', { name: 'Edit reply' }))
    fireEvent.change(screen.getByLabelText('Reply draft content'), { target: { value: 'Keep my unsaved edit.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }))
    await screen.findByRole('alert')
    expect((screen.getByLabelText('Reply draft content') as HTMLTextAreaElement).value).toBe('Keep my unsaved edit.')
    expect(changed).not.toHaveBeenCalled()
  })

  it('loads the preserved revision history', async () => {
    show()
    fireEvent.click(screen.getByText('Draft revision history'))
    await screen.findByText('Revision 1 · created · Local AI')
    expect(screen.getByText(draft.reply_text)).toBeTruthy()
  })

  it('disables review when workflow state is unavailable', () => {
    show(draft, null)
    expect((screen.getByRole('button', { name: 'Approve' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Edit reply' }) as HTMLButtonElement).disabled).toBe(true)
  })
})
