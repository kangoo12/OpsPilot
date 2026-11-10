// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import TicketDashboard from './TicketDashboard'
import { createTicket, getTicket, listTickets, type Ticket, type TicketPage } from './api'

vi.mock('./api', async () => ({
  ...await vi.importActual<typeof import('./api')>('./api'),
  createTicket: vi.fn(), getTicket: vi.fn(), listTickets: vi.fn(),
}))

const ticket: Ticket = {
  id: 'd1dcc2d5-c28b-4ab1-9aaa-48dd74543210',
  message: 'Η παραγγελία μου #GR-1042 δεν έφτασε.', category: 'delivery', priority: 'medium',
  order_id: 'GR-1042', customer_intent: 'Εντοπισμός παραγγελίας', reason: 'Καθυστέρηση παράδοσης.',
  status: 'new', created_at: '2026-11-10T18:00:00Z',
}
function page(items: Ticket[] = []): TicketPage {
  return { items, counts: { total: items.length, new: items.length, high: 0, urgent: 0 }, limit: 20, offset: 0 }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listTickets).mockResolvedValue(page())
  vi.mocked(getTicket).mockResolvedValue(ticket)
  vi.mocked(createTicket).mockResolvedValue(ticket)
})
afterEach(() => { cleanup(); vi.useRealTimers() })

async function showDashboard() {
  render(<TicketDashboard />)
  await screen.findByText(/No tickets yet/)
}

describe('ticket dashboard', () => {
  it('flags tickets requiring order verification in the list', async () => {
    vi.mocked(listTickets).mockResolvedValue(page([{ ...ticket, requires_human_review: true }]))
    render(<TicketDashboard />)
    await screen.findByRole('button', { name: `View ticket ${ticket.id}` })
    expect(screen.getByText('Human review')).toBeTruthy()
  })
  it('shows an empty list and counts', async () => {
    await showDashboard()
    const counts = screen.getByRole('region', { name: 'Ticket counts' })
    expect(within(counts).getAllByText('0')).toHaveLength(4)
  })

  it('validates empty and excessively long customer messages', async () => {
    await showDashboard()
    fireEvent.click(screen.getByRole('button', { name: 'Classify & save ticket' }))
    expect(screen.getByRole('alert').textContent).toContain('Enter a customer message')
    fireEvent.change(screen.getByLabelText('Customer message'), { target: { value: 'α'.repeat(5001) } })
    fireEvent.click(screen.getByRole('button', { name: 'Classify & save ticket' }))
    expect(screen.getByRole('alert').textContent).toContain('5,000 characters or fewer')
    expect(createTicket).not.toHaveBeenCalled()
  })

  it('submits Greek input, prevents duplicate submission, and shows the saved ticket', async () => {
    await showDashboard()
    let finish!: (value: Ticket) => void
    vi.mocked(createTicket).mockReturnValue(new Promise(resolve => { finish = resolve }))
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    fireEvent.change(screen.getByLabelText('Customer message'), { target: { value: ticket.message } })
    fireEvent.click(screen.getByRole('button', { name: 'Classify & save ticket' }))
    const loading = screen.getByRole('button', { name: 'Classifying locally…' }) as HTMLButtonElement
    expect(loading.disabled).toBe(true)
    fireEvent.click(loading)
    expect(createTicket).toHaveBeenCalledTimes(1)
    expect(createTicket).toHaveBeenCalledWith(ticket.message)
    finish(ticket)
    await screen.findByText('Ticket classified and saved. Review its details below.')
    const details = await screen.findByRole('region', { name: 'Ticket details' })
    expect(within(details).getByText(ticket.reason).textContent).toBe(ticket.reason)
    expect(within(details).getByText('GR-1042')).toBeTruthy()
    expect((screen.getByLabelText('Customer message') as HTMLTextAreaElement).value).toBe('')
    await screen.findByRole('button', { name: `View ticket ${ticket.id}` })
  })

  it('preserves the message and reports AI failure without a fake ticket', async () => {
    await showDashboard()
    vi.mocked(createTicket).mockRejectedValue(new Error('Ollama is unavailable. No ticket was saved.'))
    fireEvent.change(screen.getByLabelText('Customer message'), { target: { value: 'My payment failed.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Classify & save ticket' }))
    expect((await screen.findByRole('alert')).textContent).toContain('No ticket was saved')
    expect((screen.getByLabelText('Customer message') as HTMLTextAreaElement).value).toBe('My payment failed.')
    expect(screen.queryByRole('region', { name: 'Ticket details' })).toBeNull()
  })

  it('loads individual details and renders missing order IDs honestly', async () => {
    const noOrder = { ...ticket, order_id: null }
    vi.mocked(listTickets).mockResolvedValue(page([noOrder]))
    vi.mocked(getTicket).mockResolvedValue(noOrder)
    render(<TicketDashboard />)
    fireEvent.click(await screen.findByRole('button', { name: `View ticket ${ticket.id}` }))
    const details = await screen.findByRole('region', { name: 'Ticket details' })
    expect(within(details).getByText('Not provided')).toBeTruthy()
    expect(getTicket).toHaveBeenCalledWith(ticket.id, expect.any(AbortSignal))
  })

  it('refreshes after a failed ticket-list request', async () => {
    vi.mocked(listTickets).mockRejectedValueOnce(new Error('Cannot load tickets.'))
    render(<TicketDashboard />)
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: 'Refresh tickets' }))
    await screen.findByText(/No tickets yet/)
    expect(listTickets).toHaveBeenCalledTimes(2)
  })

  it('renders customer and AI strings as text, never HTML', async () => {
    const unsafe = { ...ticket, message: '<img src=x onerror=alert(1)>', reason: '<script>alert(1)</script>' }
    vi.mocked(listTickets).mockResolvedValue(page([unsafe]))
    vi.mocked(getTicket).mockResolvedValue(unsafe)
    render(<TicketDashboard />)
    fireEvent.click(await screen.findByRole('button', { name: `View ticket ${ticket.id}` }))
    await screen.findByRole('region', { name: 'Ticket details' })
    expect(document.querySelector('img')).toBeNull()
    expect(document.querySelector('script')).toBeNull()
    expect(screen.getByText('<script>alert(1)</script>')).toBeTruthy()
  })

  it('paginates and keeps global counts', async () => {
    vi.mocked(listTickets).mockResolvedValue({ ...page([ticket]), counts: { total: 21, new: 21, high: 0, urgent: 0 } })
    render(<TicketDashboard />)
    const next = await screen.findByRole('button', { name: 'Next' })
    fireEvent.click(next)
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), ''))
  })
})

describe('ticket search', () => {
  function search(value: string) {
    fireEvent.change(screen.getByLabelText('Search tickets'), { target: { value } })
  }
  async function advance(milliseconds = 300) {
    await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds) })
  }

  it('debounces typing for 300ms and updates matching tickets and counts', async () => {
    await showDashboard()
    vi.useFakeTimers()
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    search('GR')
    await advance(200)
    search('GR-1042')
    await advance(299)
    expect(listTickets).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Loading tickets…')).toBeTruthy()
    await advance(1)
    expect(listTickets).toHaveBeenCalledTimes(2)
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'GR-1042')
    expect(screen.getByRole('button', { name: `View ticket ${ticket.id}` })).toBeTruthy()
    expect(screen.getByText('1 matching tickets')).toBeTruthy()
  })

  it('resets pagination for a search and preserves the query on subsequent pages', async () => {
    vi.mocked(listTickets).mockResolvedValue({ ...page([ticket]), counts: { total: 41, new: 41, high: 0, urgent: 0 } })
    render(<TicketDashboard />)
    fireEvent.click(await screen.findByRole('button', { name: 'Next' }))
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), ''))
    vi.useFakeTimers()
    search('delivery')
    await advance()
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'delivery')
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await advance(0)
    expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), 'delivery')
  })

  it('shows no results and clears back to the unsearched list', async () => {
    await showDashboard()
    vi.useFakeTimers()
    search('missing')
    await advance()
    expect(screen.getByText(/No results found/)).toBeTruthy()
    expect(screen.getByText('0 matching tickets')).toBeTruthy()
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    await advance()
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), '')
    expect((screen.getByLabelText('Search tickets') as HTMLInputElement).value).toBe('')
    expect(screen.queryByRole('button', { name: 'Clear search' })).toBeNull()
    expect(screen.getByRole('button', { name: `View ticket ${ticket.id}` })).toBeTruthy()
  })

  it('reports search failures and retries the same query through refresh', async () => {
    await showDashboard()
    vi.useFakeTimers()
    vi.mocked(listTickets).mockRejectedValueOnce(new Error('Search unavailable.'))
    search('phone')
    await advance()
    expect(screen.getByRole('alert').textContent).toContain('Search unavailable.')
    fireEvent.click(screen.getByRole('button', { name: 'Refresh tickets' }))
    await advance(0)
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'phone')
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('ignores outdated responses even if the request ignores cancellation', async () => {
    await showDashboard()
    vi.useFakeTimers()
    let finishOld!: (value: TicketPage) => void
    vi.mocked(listTickets).mockReturnValueOnce(new Promise(resolve => { finishOld = resolve }))
    search('old')
    await advance()
    const oldSignal = vi.mocked(listTickets).mock.calls.at(-1)![1]!
    search('new')
    expect(oldSignal.aborted).toBe(true)
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    await advance()
    await act(async () => { finishOld(page()) })
    expect(screen.getByRole('button', { name: `View ticket ${ticket.id}` })).toBeTruthy()
    expect(screen.getByText('1 matching tickets')).toBeTruthy()
    expect(screen.queryByText(/No results found/)).toBeNull()
  })

  it('keeps the selected ticket details open when the search does not match it', async () => {
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    render(<TicketDashboard />)
    fireEvent.click(await screen.findByRole('button', { name: `View ticket ${ticket.id}` }))
    await screen.findByRole('region', { name: 'Ticket details' })
    vi.useFakeTimers()
    vi.mocked(listTickets).mockResolvedValue(page())
    search('unrelated')
    await advance()
    expect(screen.getByText(/No results found/)).toBeTruthy()
    expect(within(screen.getByRole('region', { name: 'Ticket details' })).getByText(ticket.reason)).toBeTruthy()
    expect(getTicket).toHaveBeenCalledTimes(1)
  })
})
