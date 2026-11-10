// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import TicketWorkflowPanel from './TicketWorkflowPanel'
import { documentDiscrepancy, getActivity, updateTicketStatus, type WorkflowState } from './api'

vi.mock('./api', async () => ({ ...await vi.importActual<typeof import('./api')>('./api'), documentDiscrepancy: vi.fn(), getActivity: vi.fn(), updateTicketStatus: vi.fn() }))
const state: WorkflowState = { status: 'new', version: 1, allowed_transitions: ['in_progress'], context_fingerprint: 'a'.repeat(64), consistency: { status: 'consistent', requires_human_review: false, issues: [], reported_products: [], reported_delivery_states: [], check_version: 'v1' }, operator: 'Local Operator', identity_is_authenticated: false, resolution: null }
const changed = vi.fn()
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getActivity).mockResolvedValue({ items: [{ id: 1, ticket_id: 'ticket-1', event_type: 'draft_approved', actor: 'Local Operator', created_at: '2026-11-10T20:00:00Z', data: { draft_id: 'draft-1', message_sent: false } }], total: 1 })
  vi.mocked(updateTicketStatus).mockResolvedValue({} as never)
  vi.mocked(documentDiscrepancy).mockResolvedValue(state)
})
afterEach(cleanup)
function show(value = state) { render(<TicketWorkflowPanel ticketId="ticket-1" state={value} loading={false} error="" revision={0} onChanged={changed} />) }

describe('ticket status and human discrepancy review', () => {
  it('allows only valid transitions and confirms status changes', async () => {
    show()
    expect(screen.queryByRole('option', { name: 'Resolved' })).toBeNull()
    fireEvent.change(screen.getByLabelText('Ticket status'), { target: { value: 'in_progress' } })
    fireEvent.click(screen.getByRole('button', { name: 'Update status' }))
    expect(updateTicketStatus).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm status change' }))
    await waitFor(() => expect(updateTicketStatus).toHaveBeenCalledWith('ticket-1', 'in_progress', 1))
  })

  it('reopens a resolved ticket explicitly', async () => {
    show({ ...state, status: 'resolved', version: 4, allowed_transitions: ['in_progress'] })
    fireEvent.change(screen.getByLabelText('Ticket status'), { target: { value: 'in_progress' } })
    fireEvent.click(screen.getByRole('button', { name: 'Reopen ticket' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm status change' }))
    await waitFor(() => expect(updateTicketStatus).toHaveBeenCalledWith('ticket-1', 'in_progress', 4))
  })

  it('requires a human resolution reason and preserves the warning', async () => {
    show({ ...state, consistency: { ...state.consistency, status: 'discrepancy', requires_human_review: true } })
    fireEvent.click(screen.getByRole('button', { name: 'Document human review' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm documentation' }))
    expect(documentDiscrepancy).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Human review reason'), { target: { value: 'Reviewed both sources; ask the customer to confirm the product.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm documentation' }))
    await waitFor(() => expect(changed).toHaveBeenCalled())
    expect(documentDiscrepancy).toHaveBeenCalledWith('ticket-1', state.context_fingerprint, 'Reviewed both sources; ask the customer to confirm the product.')
    expect(screen.getByText('Human Review Required')).toBeTruthy()
  })

  it('shows a documented decision without dismissing the discrepancy', () => {
    show({ ...state, consistency: { ...state.consistency, requires_human_review: true }, resolution: { id: 'resolution-1', reason: 'Ask for a corrected order reference.', actor: 'Local Operator', context_fingerprint: state.context_fingerprint, created_at: '2026-11-10T20:00:00Z' } })
    expect(screen.getByText('Human Review Required')).toBeTruthy()
    expect(screen.getByText('Ask for a corrected order reference.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Document human review' })).toBeNull()
  })

  it('loads the activity timeline on demand', async () => {
    show()
    expect(getActivity).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Activity History'))
    await screen.findByText('Draft approved — nothing sent')
    expect(screen.getByText(/Local Operator · demo identity, no authentication/)).toBeTruthy()
  })
})
