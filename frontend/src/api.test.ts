import { afterEach, describe, expect, it, vi } from 'vitest'
import { checkConnection, createReplyDraft, createTicket, getTicket, getTicketOrder, listDrafts, listTickets, setTicketOrder } from './api'

afterEach(() => { vi.unstubAllGlobals() })

function respond(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
  })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('connection checks', () => {
  it('reports backend and SQLite health', async () => {
    const fetchMock = respond({ status: 'ok', database: 'connected' })
    expect((await checkConnection('backend')).state).toBe('connected')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/health')
  })

  it('reports the actual model returned by the backend', async () => {
    respond({ status: 'ok', model: 'qwen3.5:9b', message: 'Ready' })
    expect(await checkConnection('ollama')).toEqual({ state: 'connected', model: 'qwen3.5:9b', message: 'Ready' })
  })

  it('preserves actionable missing-model messages on HTTP 503', async () => {
    respond({ status: 'model_missing', model: 'qwen3.5:9b', message: 'Model is not installed' }, 503)
    expect(await checkConnection('ollama')).toMatchObject({ state: 'error', message: 'Model is not installed' })
  })

  it('does not report a failed HTTP response as connected', async () => {
    respond({ status: 'ok', database: 'connected' }, 503)
    expect((await checkConnection('backend')).state).toBe('error')
  })

  it('handles an unavailable backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    expect(await checkConnection('backend')).toMatchObject({ state: 'error', message: expect.stringContaining('Start the API') })
    expect((await checkConnection('ollama')).state).toBe('error')
  })

  it('handles an unexpected proxy response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Error</html>')))
    expect((await checkConnection('backend')).state).toBe('error')
  })

  it('rejects malformed AI health data', async () => {
    respond({ status: 'ok' })
    expect((await checkConnection('ollama')).state).toBe('error')
  })
})

describe('ticket requests', () => {
  it('keeps order lookups and reply generation behind the backend', async () => {
    const mock = respond({})
    await getTicketOrder('ticket-id')
    await setTicketOrder('ticket-id', 'GR-1042')
    await createReplyDraft('ticket-id')
    await listDrafts('ticket-id')
    expect(mock.mock.calls.map(call => call[0])).toEqual(['/api/tickets/ticket-id/order', '/api/tickets/ticket-id/order', '/api/tickets/ticket-id/drafts', '/api/tickets/ticket-id/drafts'])
    expect(mock.mock.calls[1][1].method).toBe('PUT')
    expect(JSON.parse(mock.mock.calls[1][1].body)).toEqual({ order_id: 'GR-1042' })
    expect(mock.mock.calls[2][1].method).toBe('POST')
  })

  it('does not automatically retry failed draft generation', async () => {
    const mock = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', mock)
    await expect(createReplyDraft('ticket-id')).rejects.toThrow('Refresh saved drafts')
    expect(mock).toHaveBeenCalledTimes(1)
  })
  it('sends the original message only to the backend', async () => {
    const mock = respond({ id: 'ticket-id' }, 201)
    await createTicket('  Η παραγγελία μου #GR-1042 δεν ήρθε.  ')
    expect(mock.mock.calls[0][0]).toBe('/api/tickets')
    expect(JSON.parse(mock.mock.calls[0][1].body)).toEqual({ message: '  Η παραγγελία μου #GR-1042 δεν ήρθε.  ' })
  })

  it('shows server classification errors without substituting a ticket', async () => {
    respond({ detail: { code: 'ai_unavailable', message: 'Cannot reach local Ollama. No ticket was saved.' } }, 503)
    await expect(createTicket('Hello')).rejects.toThrow('Cannot reach local Ollama')
  })

  it('warns about an uncertain save after a network error and never retries', async () => {
    const mock = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', mock)
    await expect(createTicket('Hello')).rejects.toThrow('refresh the list before submitting again')
    expect(mock).toHaveBeenCalledTimes(1)
  })

  it('loads paginated tickets and individual details', async () => {
    const mock = respond({})
    await listTickets(20)
    await getTicket('a/b')
    expect(mock.mock.calls[0][0]).toBe('/api/tickets?limit=20&offset=20')
    expect(mock.mock.calls[1][0]).toBe('/api/tickets/a%2Fb')
  })

  it('encodes the search parameter safely and preserves pagination and cancellation', async () => {
    const mock = respond({})
    const controller = new AbortController()
    await listTickets(40, controller.signal, '  GR-1042 & Έκπτωση 50%  ')
    const url = new URL(mock.mock.calls[0][0], 'http://localhost')
    expect(url.searchParams.get('search')).toBe('GR-1042 & Έκπτωση 50%')
    expect(url.searchParams.get('limit')).toBe('20')
    expect(url.searchParams.get('offset')).toBe('40')
    controller.abort()
    expect(mock.mock.calls[0][1].signal.aborted).toBe(true)
    await listTickets(0, undefined, '   ')
    expect(mock.mock.calls[1][0]).toBe('/api/tickets?limit=20&offset=0')
  })
})
