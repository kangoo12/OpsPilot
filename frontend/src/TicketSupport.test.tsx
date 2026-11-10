// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import TicketSupport from './TicketSupport'
import { createReplyDraft, getSupportPolicies, getTicketOrder, getWorkflow, listDrafts, setTicketOrder, type ConsistencyCheck, type ReplyDraft, type Ticket, type TicketOrder } from './api'

vi.mock('./api', async () => ({
  ...await vi.importActual<typeof import('./api')>('./api'),
  createReplyDraft: vi.fn(), getSupportPolicies: vi.fn(), getTicketOrder: vi.fn(), getWorkflow: vi.fn(), listDrafts: vi.fn(), setTicketOrder: vi.fn(),
}))
const ticket: Ticket = {
  id: 'e27e8e6c-bfc4-43cd-9e39-10e167574144', message: 'Where is my order #DEMO-LAMP-9001?',
  category: 'delivery', priority: 'medium', order_id: 'DEMO-LAMP-9001', customer_intent: 'Locate order',
  reason: 'Routine delivery request.', status: 'new', created_at: '2026-11-10T19:00:00Z',
}
const order: TicketOrder = {
  reference_order_id: 'DEMO-LAMP-9001', extracted_order_id: 'DEMO-LAMP-9001', source: 'extracted', lookup_status: 'found',
  order: { id: 'DEMO-LAMP-9001', product: 'LumaLite desk lamp', order_date: '2026-11-06', delivery_status: 'in_transit',
    estimated_delivery_date: '2026-11-14', return_eligibility: 'not_started', warranty_eligibility: 'review_available',
    snapshot_date: '2026-11-10', is_synthetic: true },
}
const draft: ReplyDraft = {
  id: 'a27e8e6c-bfc4-43cd-9e39-10e167574144', ticket_id: ticket.id,
  reply_text: 'Thank you for getting in touch. The order record lists your lamp as in transit.',
  language: 'en', status: 'pending_review', model: 'qwen3.5:9b', order_context: order,
  policy_version: 'aster-demo-2026-11-v1', created_at: '2026-11-10T19:01:00Z',
}

const conflict: ConsistencyCheck = {
  status: 'discrepancy', requires_human_review: true, check_version: 'reported-facts-v1',
  reported_products: ['smartphone'], reported_delivery_states: ['received'],
  issues: [
    { code: 'product_mismatch', message: 'The reported product differs from the order record.', customer_reported: 'smartphone', order_recorded: 'LumaLite desk lamp' },
    { code: 'delivery_status_mismatch', message: 'Delivery statements need human review.', customer_reported: 'received', order_recorded: 'in_transit' },
  ],
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getTicketOrder).mockResolvedValue(order)
  vi.mocked(listDrafts).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(getSupportPolicies).mockResolvedValue({ version: draft.policy_version, is_fictional: true, policies: ['Estimates are not guarantees.'] })
  vi.mocked(createReplyDraft).mockResolvedValue(draft)
  vi.mocked(setTicketOrder).mockResolvedValue(order)
  vi.mocked(getWorkflow).mockResolvedValue({ status: 'new', version: 1, allowed_transitions: ['in_progress'], context_fingerprint: 'a'.repeat(64), operator: 'Local Operator', identity_is_authenticated: false, resolution: null,
    consistency: { status: 'consistent', requires_human_review: false, issues: [], reported_products: [], reported_delivery_states: [], check_version: 'reported-facts-v1' } })
})
afterEach(cleanup)

async function show() {
  render(<TicketSupport ticket={ticket} />)
  await waitFor(() => expect((screen.getByRole('button', { name: 'Generate suggested reply' }) as HTMLButtonElement).disabled).toBe(false))
}

describe('verified orders and suggested replies', () => {
  it('shows material discrepancies and both sources without assuming a cause', async () => {
    vi.mocked(getTicketOrder).mockResolvedValue({ ...order, consistency: conflict })
    await show()
    const warning = screen.getByRole('alert', { name: 'Order consistency warning' })
    expect(warning.textContent).toContain('human review required')
    expect(warning.textContent).toContain('Customer reports: smartphone')
    expect(warning.textContent).toContain('Order record: LumaLite desk lamp')
    expect(warning.textContent).toContain('Neither source has been reconciled')
  })

  it('keeps older contradictory drafts collapsed and unchanged', async () => {
    vi.mocked(getTicketOrder).mockResolvedValue({ ...order, consistency: conflict })
    vi.mocked(listDrafts).mockResolvedValue({ items: [draft], total: 1 })
    await show()
    expect(screen.queryByTestId('reply-text')).toBeNull()
    const old = screen.getByTestId('historical-reply-text')
    expect(old.textContent).toBe(draft.reply_text)
    expect(old.closest('details')?.hasAttribute('open')).toBe(false)
    expect(screen.getByText(/Historical draft — conflicting order facts/)).toBeTruthy()
  })

  it('warns about historical snapshot conflicts even after the current reference is corrected', async () => {
    vi.mocked(listDrafts).mockResolvedValue({ items: [{ ...draft, snapshot_consistency: conflict }], total: 1 })
    await show()
    expect(screen.queryByTestId('reply-text')).toBeNull()
    expect(screen.getByTestId('historical-reply-text').textContent).toBe(draft.reply_text)
    expect(screen.getByText(/Historical draft — conflicting order facts/)).toBeTruthy()
  })

  it('displays a conflict-aware neutral draft with the warning still visible', async () => {
    const conflictingOrder = { ...order, consistency: conflict }
    vi.mocked(getTicketOrder).mockResolvedValue(conflictingOrder)
    vi.mocked(createReplyDraft).mockResolvedValue({ ...draft, order_context: conflictingOrder, reply_text: 'The details need clarification. Please confirm the product and delivery information.' })
    await show()
    fireEvent.click(screen.getByRole('button', { name: 'Generate suggested reply' }))
    const text = await screen.findByTestId('reply-text')
    expect(text.textContent).toContain('need clarification')
    expect(text.textContent).not.toContain('in transit')
    expect(screen.getByRole('alert', { name: 'Order consistency warning' })).toBeTruthy()
    expect(screen.getByText('Pending human review')).toBeTruthy()
  })

  it('refreshes ticket flags when an explicit manual correction resolves the mismatch', async () => {
    vi.mocked(getTicketOrder).mockResolvedValue({ ...order, consistency: conflict })
    vi.mocked(setTicketOrder).mockResolvedValue({ ...order, reference_order_id: '7821', source: 'manual', consistency: { ...conflict, status: 'consistent', requires_human_review: false, issues: [] } })
    const changed = vi.fn()
    render(<TicketSupport ticket={ticket} onOrderChanged={changed} />)
    await screen.findByRole('alert', { name: 'Order consistency warning' })
    await waitFor(() => expect((screen.getByRole('button', { name: 'Save & lookup' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.change(screen.getByLabelText('Order ID for lookup'), { target: { value: '7821' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & lookup' }))
    await waitFor(() => expect(changed).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('alert', { name: 'Order consistency warning' })).toBeNull()
    expect(screen.getByText(/No material discrepancy detected/)).toBeTruthy()
  })

  it('shows verified synthetic details and unapproved support eligibility', async () => {
    await show()
    const region = screen.getByRole('region', { name: 'Order details' })
    expect(within(region).getByText('LumaLite desk lamp')).toBeTruthy()
    expect(within(region).getByText(/Found in demo records/)).toBeTruthy()
    expect(within(region).getByText(/not an approval/)).toBeTruthy()
    expect(within(region).getByText(/not a guarantee/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /send/i })).toBeNull()
  })

  it('distinguishes unknown and missing order information without invented facts', async () => {
    vi.mocked(getTicketOrder).mockResolvedValue({ ...order, lookup_status: 'unknown', order: null, reference_order_id: 'MISSING-999' })
    await show()
    expect(screen.getByText(/Unknown order: MISSING-999/)).toBeTruthy()
    expect(screen.queryByText('LumaLite desk lamp')).toBeNull()
    cleanup()
    vi.mocked(getTicketOrder).mockResolvedValue({ ...order, lookup_status: 'not_provided', reference_order_id: null, order: null })
    await show()
    expect(screen.getByText(/No order ID provided/)).toBeTruthy()
  })

  it('shows an unknown ETA explicitly', async () => {
    vi.mocked(getTicketOrder).mockResolvedValue({ ...order, order: { ...order.order!, estimated_delivery_date: null } })
    await show()
    expect(screen.getByText('Not available in verified records')).toBeTruthy()
  })

  it('saves manual corrections, keeps original extraction, and flags old drafts', async () => {
    vi.mocked(listDrafts).mockResolvedValue({ items: [draft], total: 1 })
    const corrected: TicketOrder = { ...order, source: 'manual', reference_order_id: 'GR-1042', order: { ...order.order!, id: 'GR-1042', estimated_delivery_date: null } }
    vi.mocked(setTicketOrder).mockResolvedValue(corrected)
    await show()
    fireEvent.change(screen.getByLabelText('Order ID for lookup'), { target: { value: 'GR-1042' } })
    expect((screen.getByRole('button', { name: 'Generate suggested reply' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Save & lookup' }))
    await screen.findByText(/Found in demo records · #GR-1042/)
    expect(setTicketOrder).toHaveBeenCalledWith(ticket.id, 'GR-1042')
    expect(screen.getByText(/The order reference or verified facts have changed/)).toBeTruthy()
    expect(screen.getByText(/Original extracted ID/).textContent).toContain('DEMO-LAMP-9001')
  })

  it('clears a reference without changing the extracted ID', async () => {
    await show()
    fireEvent.change(screen.getByLabelText('Order ID for lookup'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save & lookup' }))
    await waitFor(() => expect(setTicketOrder).toHaveBeenCalledWith(ticket.id, null))
  })

  it('shows lookup errors and allows an explicit refresh', async () => {
    vi.mocked(getTicketOrder).mockRejectedValueOnce(new Error('Order lookup unavailable.'))
    render(<TicketSupport ticket={ticket} />)
    await screen.findByRole('alert')
    expect((screen.getByRole('button', { name: 'Generate suggested reply' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Refresh order & drafts' }))
    await screen.findByText(/Found in demo records/)
  })

  it('shows generation loading, prevents duplicates, and saves only pending drafts', async () => {
    let finish!: (draft: ReplyDraft) => void
    vi.mocked(createReplyDraft).mockReturnValue(new Promise(resolve => { finish = resolve }))
    await show()
    fireEvent.click(screen.getByRole('button', { name: 'Generate suggested reply' }))
    const loading = screen.getByRole('button', { name: 'Generating locally…' }) as HTMLButtonElement
    expect(loading.disabled).toBe(true)
    fireEvent.click(loading)
    expect(createReplyDraft).toHaveBeenCalledTimes(1)
    finish(draft)
    await screen.findByText(draft.reply_text)
    expect(screen.getByText('Pending human review')).toBeTruthy()
    expect(createReplyDraft).toHaveBeenCalledWith(ticket.id)
    expect(screen.queryByRole('button', { name: /send/i })).toBeNull()
  })

  it('loads persisted draft history and lets the user view earlier drafts', async () => {
    const previous = { ...draft, id: 'b27e8e6c-bfc4-43cd-9e39-10e167574144', reply_text: 'Previous grounded draft.', created_at: '2026-11-10T19:00:00Z' }
    vi.mocked(listDrafts).mockResolvedValue({ items: [draft, previous], total: 2 })
    await show()
    expect(screen.getByText(draft.reply_text)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Saved drafts'), { target: { value: previous.id } })
    expect(screen.getByText(previous.reply_text)).toBeTruthy()
  })

  it('reports failed inference without replacing a previous saved draft', async () => {
    vi.mocked(listDrafts).mockResolvedValue({ items: [draft], total: 1 })
    vi.mocked(createReplyDraft).mockRejectedValue(new Error('Cannot reach local Ollama. No draft was saved.'))
    await show()
    fireEvent.click(screen.getByRole('button', { name: 'Generate suggested reply' }))
    expect((await screen.findByRole('alert')).textContent).toContain('No draft was saved')
    expect(screen.getByText(draft.reply_text)).toBeTruthy()
  })

  it('renders AI draft text safely', async () => {
    vi.mocked(listDrafts).mockResolvedValue({ items: [{ ...draft, reply_text: '<img src=x onerror=alert(1)>' }], total: 1 })
    await show()
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy()
    expect(document.querySelector('img')).toBeNull()
  })

  it('reports unavailable policy details without inventing policy text', async () => {
    vi.mocked(getSupportPolicies).mockRejectedValue(new Error('Offline'))
    await show()
    expect((await screen.findByRole('alert')).textContent).toContain('Policy details could not be loaded')
    expect(screen.queryByText('Estimates are not guarantees.')).toBeNull()
  })
})
