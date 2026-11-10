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
  requires_human_review?: boolean
  consistency?: ConsistencyCheck
}
export type TicketPage = {
  items: Ticket[]
  counts: { total: number; new: number; high: number; urgent: number }
  limit: number
  offset: number
}

export class ApiError extends Error {}

async function ticketRequest<T>(path: string, options: RequestInit = {}, messages?: { failure?: string; invalid?: string }): Promise<T> {
  let response: Response
  try {
    const timeout = AbortSignal.timeout(options.method === 'POST' ? 310000 : 15000)
    response = await fetch(path, {
      cache: 'no-store', ...options,
      signal: options.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
    })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new ApiError(messages?.failure ?? (options.method === 'POST'
      ? 'Could not confirm whether the ticket was saved. Check the backend and refresh the list before submitting again.'
      : 'Cannot load tickets. Check that the backend is running and try again.'))
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
    throw new ApiError(response.status === 422 ? messages?.invalid ?? 'Enter a message between 1 and 5,000 characters.' : 'The request failed. Please try again.')
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

export type Order = {
  id: string
  product: string
  order_date: string
  delivery_status: 'processing' | 'in_transit' | 'delayed' | 'delivered' | 'cancelled' | 'returned'
  estimated_delivery_date: string | null
  return_eligibility: 'review_available' | 'not_eligible' | 'not_started' | 'unknown'
  warranty_eligibility: 'review_available' | 'not_eligible' | 'unknown'
  snapshot_date: string
  is_synthetic: true
}
export type TicketOrder = {
  reference_order_id: string | null
  extracted_order_id: string | null
  source: 'extracted' | 'manual'
  lookup_status: 'found' | 'unknown' | 'not_provided'
  order: Order | null
  consistency?: ConsistencyCheck
}
export type ConsistencyCheck = {
  status: 'consistent' | 'discrepancy' | 'unknown_order' | 'no_order_id' | 'not_checked'
  requires_human_review: boolean
  issues: { code: string; message: string; customer_reported: string | null; order_recorded: string | null }[]
  reported_products: string[]
  reported_delivery_states: string[]
  check_version: string
}
export type ReplyDraft = {
  id: string
  ticket_id: string
  reply_text: string
  language: 'en' | 'el'
  status: 'pending_review'
  model: 'qwen3.5:9b'
  order_context: TicketOrder
  policy_version: string
  created_at: string
  snapshot_consistency?: ConsistencyCheck
}
export type DraftPage = { items: ReplyDraft[]; total: number }
export type SupportPolicies = { version: string; is_fictional: true; policies: string[] }

export function getTicketOrder(id: string, signal?: AbortSignal): Promise<TicketOrder> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}/order`, { signal }, { failure: 'Cannot load verified order details. Check the backend and retry.' })
}

export function setTicketOrder(id: string, orderId: string | null): Promise<TicketOrder> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}/order`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: orderId }),
  }, { invalid: 'Enter a valid order ID of up to 64 letters, numbers, hyphens or slashes.', failure: 'Could not confirm the order correction. Refresh this ticket before trying again.' })
}

export function listDrafts(id: string, signal?: AbortSignal): Promise<DraftPage> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}/drafts`, { signal }, { failure: 'Cannot load saved drafts. Check the backend and retry.' })
}

export function createReplyDraft(id: string): Promise<ReplyDraft> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}/drafts`, { method: 'POST' }, {
    failure: 'Could not confirm whether the draft was saved. Refresh saved drafts before generating again.',
  })
}

export function getSupportPolicies(signal?: AbortSignal): Promise<SupportPolicies> {
  return ticketRequest('/api/support-policies', { signal })
}
