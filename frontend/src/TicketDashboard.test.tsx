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
  fireEvent.click(screen.getByRole('button', { name: 'New customer message' }))
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
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), '', {}, 'newest'))
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
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'GR-1042', {}, 'newest')
    expect(screen.getByRole('button', { name: `View ticket ${ticket.id}` })).toBeTruthy()
    expect(screen.getByText('1 matching tickets')).toBeTruthy()
  })

  it('resets pagination for a search and preserves the query on subsequent pages', async () => {
    vi.mocked(listTickets).mockResolvedValue({ ...page([ticket]), counts: { total: 41, new: 41, high: 0, urgent: 0 } })
    render(<TicketDashboard />)
    fireEvent.click(await screen.findByRole('button', { name: 'Next' }))
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), '', {}, 'newest'))
    vi.useFakeTimers()
    search('delivery')
    await advance()
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'delivery', {}, 'newest')
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await advance(0)
    expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), 'delivery', {}, 'newest')
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
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), '', {}, 'newest')
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
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'phone', {}, 'newest')
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

describe('ticket filters', () => {
  it('sorts with search and filters and resets pagination', async () => {
    vi.mocked(listTickets).mockResolvedValue({ ...page([ticket]), counts: { total: 41, new: 41, high: 0, urgent: 0 } })
    render(<TicketDashboard />)
    await screen.findByRole('button', { name: 'Next' })
    fireEvent.change(screen.getByLabelText('Search tickets'), { target: { value: 'parcel' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Category' }), { target: { value: 'delivery' } })
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'parcel', { category: 'delivery' }, 'newest'))
    await waitFor(() => expect((screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), 'parcel', { category: 'delivery' }, 'newest'))
    fireEvent.change(screen.getByRole('combobox', { name: 'Sort tickets' }), { target: { value: 'priority_high' } })
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'parcel', { category: 'delivery' }, 'priority_high'))
  })
  function filter(label: string, value: string) {
    fireEvent.change(screen.getByRole('combobox', { name: label }), { target: { value } })
  }

  it.each([
    ['Category', 'returns', 'category'],
    ['Priority', 'urgent', 'priority'],
    ['Status', 'waiting_for_customer', 'status'],
  ])('requests the individual %s filter and displays matching counts', async (label, value, key) => {
    await showDashboard()
    expect((screen.getByRole('combobox', { name: label }) as HTMLSelectElement).value).toBe('')
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    filter(label, value)
    await screen.findByText('1 matching tickets')
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), '', { [key]: value }, 'newest')
    expect(screen.getByRole('button', { name: `View ticket ${ticket.id}` })).toBeTruthy()
    filter(label, '')
    await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), '', { [key]: '' }, 'newest'))
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('combines all filters with debounced search and clears only filters', async () => {
    await showDashboard()
    vi.useFakeTimers()
    fireEvent.change(screen.getByLabelText('Search tickets'), { target: { value: 'GR-1042' } })
    filter('Category', 'delivery')
    filter('Priority', 'high')
    filter('Status', 'in_progress')
    expect(listTickets).toHaveBeenCalledTimes(1)
    await act(async () => { await vi.advanceTimersByTimeAsync(300) })
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'GR-1042', {
      category: 'delivery', priority: 'high', status: 'in_progress',
    }, 'newest')
    expect(screen.getByText('0 matching tickets')).toBeTruthy()
    expect(screen.getByText(/No results found/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), 'GR-1042', {}, 'newest')
    expect((screen.getByLabelText('Search tickets') as HTMLInputElement).value).toBe('GR-1042')
    for (const label of ['Category', 'Priority', 'Status']) {
      expect((screen.getByRole('combobox', { name: label }) as HTMLSelectElement).value).toBe('')
    }
  })

  it.each([['Category', 'delivery'], ['Priority', 'high'], ['Status', 'new']])(
    'resets pagination when %s changes and when filters are cleared', async (label, value) => {
      vi.mocked(listTickets).mockResolvedValue({ ...page([ticket]), counts: { total: 41, new: 41, high: 0, urgent: 0 } })
      render(<TicketDashboard />)
      fireEvent.click(await screen.findByRole('button', { name: 'Next' }))
      await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), '', {}, 'newest'))
      const previousCalls = vi.mocked(listTickets).mock.calls.length
      filter(label, value)
      await waitFor(() => expect(listTickets).toHaveBeenCalledTimes(previousCalls + 1))
      expect(vi.mocked(listTickets).mock.calls.at(-1)![0]).toBe(0)
      await waitFor(() => expect((screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement).disabled).toBe(false))
      fireEvent.click(screen.getByRole('button', { name: 'Next' }))
      await waitFor(() => expect(vi.mocked(listTickets).mock.calls.at(-1)![0]).toBe(20))
      fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
      await waitFor(() => expect(listTickets).toHaveBeenLastCalledWith(0, expect.any(AbortSignal), '', {}, 'newest'))
    },
  )

  it('ignores an outdated filter response after a newer filter finishes', async () => {
    await showDashboard()
    let finishOld!: (value: TicketPage) => void
    vi.mocked(listTickets).mockReturnValueOnce(new Promise(resolve => { finishOld = resolve }))
    filter('Category', 'returns')
    const oldSignal = vi.mocked(listTickets).mock.calls.at(-1)![1]!
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    filter('Category', 'delivery')
    expect(oldSignal.aborted).toBe(true)
    await screen.findByText('1 matching tickets')
    await act(async () => { finishOld(page()) })
    expect(screen.getByRole('button', { name: `View ticket ${ticket.id}` })).toBeTruthy()
    expect(screen.getByText('1 matching tickets')).toBeTruthy()
  })

  it('keeps selected ticket details open when filters exclude the ticket', async () => {
    vi.mocked(listTickets).mockResolvedValue(page([ticket]))
    render(<TicketDashboard />)
    fireEvent.click(await screen.findByRole('button', { name: `View ticket ${ticket.id}` }))
    await screen.findByRole('region', { name: 'Ticket details' })
    vi.mocked(listTickets).mockResolvedValue(page())
    filter('Category', 'returns')
    await screen.findByText(/No results found/)
    expect(within(screen.getByRole('region', { name: 'Ticket details' })).getByText(ticket.reason)).toBeTruthy()
    expect(getTicket).toHaveBeenCalledTimes(1)
  })
})
