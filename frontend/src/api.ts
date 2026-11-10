export type Connection = {
  state: 'checking' | 'connected' | 'error'
  message: string
  model?: string
}

export async function checkConnection(
  service: 'backend' | 'ollama',
  signal?: AbortSignal,
): Promise<Connection> {
  const path = service === 'backend' ? '/api/health' : '/api/health/ollama'
  try {
    const timeout = AbortSignal.timeout(35000)
    const response = await fetch(path, {
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      cache: 'no-store',
    })
    const body: unknown = await response.json()
    if (typeof body !== 'object' || body === null || !('status' in body)) {
      throw new Error('Invalid health response')
    }
    if (service === 'backend') {
      if (response.ok && body.status === 'ok' && 'database' in body && body.database === 'connected') {
        return { state: 'connected', message: 'The API is running and SQLite is connected.' }
      }
      return { state: 'error', message: 'The API responded, but its health check failed. Check the backend terminal.' }
    }
    if (!('model' in body) || typeof body.model !== 'string' || !('message' in body) || typeof body.message !== 'string') {
      throw new Error('Invalid AI health response')
    }
    return {
      state: response.ok && body.status === 'ok' ? 'connected' : 'error',
      message: body.message,
      model: body.model,
    }
  } catch {
    return {
      state: 'error',
      message: service === 'backend'
        ? 'Cannot reach the backend. Start the API and try again.'
        : 'Cannot check local AI. Make sure the backend is running, then try again.',
    }
  }
}

export const MAX_MESSAGE_LENGTH = 5000
export const categories = ['delivery', 'returns', 'payments', 'technical_support', 'other'] as const
export const priorities = ['low', 'medium', 'high', 'urgent'] as const
export type Category = typeof categories[number]
export type Priority = typeof priorities[number]
export type Ticket = {
  id: string
  message: string
  category: Category
  priority: Priority
  order_id: string | null
  customer_intent: string
  reason: string
  status: 'new'
  created_at: string
}
export type TicketPage = {
  items: Ticket[]
  counts: { total: number; new: number; high: number; urgent: number }
  limit: number
  offset: number
}

export class ApiError extends Error {}

async function ticketRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    const timeout = AbortSignal.timeout(options.method === 'POST' ? 310000 : 15000)
    response = await fetch(path, {
      cache: 'no-store', ...options,
      signal: options.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
    })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new ApiError(options.method === 'POST'
      ? 'Could not confirm whether the ticket was saved. Check the backend and refresh the list before submitting again.'
      : 'Cannot load tickets. Check that the backend is running and try again.')
  }
  let body: unknown
  try { body = await response.json() } catch {
    throw new ApiError('The backend returned an unexpected response. Refresh the ticket list before retrying.')
  }
  if (!response.ok) {
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const detail = body.detail
      if (typeof detail === 'object' && detail !== null && 'message' in detail && typeof detail.message === 'string') {
        throw new ApiError(detail.message)
      }
    }
    throw new ApiError(response.status === 422 ? 'Enter a message between 1 and 5,000 characters.' : 'The request failed. Please try again.')
  }
  return body as T
}

export function createTicket(message: string): Promise<Ticket> {
  return ticketRequest('/api/tickets', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }),
  })
}

export function listTickets(offset = 0, signal?: AbortSignal): Promise<TicketPage> {
  return ticketRequest(`/api/tickets?limit=20&offset=${offset}`, { signal })
}

export function getTicket(id: string, signal?: AbortSignal): Promise<Ticket> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}`, { signal })
}
