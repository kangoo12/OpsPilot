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
  status: TicketStatus
  workflow_version?: number
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

export type TicketFilters = { category?: Category | ''; priority?: Priority | ''; status?: TicketStatus | '' }
export const sortLabels = { newest: 'Newest first', oldest: 'Oldest first', priority_high: 'Highest priority first', priority_low: 'Lowest priority first', updated: 'Recently updated first' }
export type TicketSort = keyof typeof sortLabels

export function listTickets(offset = 0, signal?: AbortSignal, search = '', filters: TicketFilters = {}, sort: TicketSort = 'newest'): Promise<TicketPage> {
  const query = new URLSearchParams({ limit: '20', offset: String(offset) })
  if (search.trim()) query.set('search', search.trim())
  if (sort !== 'newest') query.set('sort', sort)
  for (const [key, value] of Object.entries(filters)) {
    if (value) query.set(key, value)
  }
  return ticketRequest(`/api/tickets?${query}`, { signal })
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
  context_fingerprint?: string
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
  status: 'pending_review' | 'approved' | 'rejected'
  model: 'qwen3.5:9b'
  order_context: TicketOrder
  policy_version: string
  created_at: string
  snapshot_consistency?: ConsistencyCheck
  original_content?: string
  version?: number
  updated_at?: string | null
  approved_at?: string | null
  rejected_at?: string | null
  reviewer?: string | null
  rejection_reason?: string | null
  parent_draft_id?: string | null
  origin?: string
  revision_count?: number
  approval_blockers?: string[]
  review_context?: TicketOrder | null
}
export type DraftPage = { items: ReplyDraft[]; total: number }
export type SupportPolicies = { version: string; is_fictional: true; policies: string[] }

export function getTicketOrder(id: string, signal?: AbortSignal): Promise<TicketOrder> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}/order`, { signal }, { failure: 'Cannot load verified order details. Check the backend and retry.' })
}

export function setTicketOrder(id: string, orderId: string | null, expectedContext?: string): Promise<TicketOrder> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}/order`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: orderId, ...(expectedContext ? { expected_context_fingerprint: expectedContext } : {}) }),
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

export type TicketStatus = 'new' | 'in_progress' | 'waiting_for_customer' | 'resolved'
export const statusLabels: Record<TicketStatus, string> = { new: 'New', in_progress: 'In Progress', waiting_for_customer: 'Waiting for Customer', resolved: 'Resolved' }
export type WorkflowState = {
  status: TicketStatus; version: number; allowed_transitions: TicketStatus[]; context_fingerprint: string
  consistency: ConsistencyCheck; operator: string; identity_is_authenticated: false
  resolution: { id: string; reason: string; actor: string; created_at: string; context_fingerprint: string } | null
}
export type ActivityEvent = { id: number; ticket_id: string; event_type: string; actor: string; created_at: string; data: Record<string, unknown> }
export type ActivityPage = { items: ActivityEvent[]; total: number }
export type DraftRevision = { draft_id: string; version: number; content: string; status: string; actor: string; action: string; reason: string | null; created_at: string }

function workflowRequest<T>(path: string, method: string, body: unknown): Promise<T> {
  return ticketRequest(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, {
    failure: 'Could not confirm this change. Refresh the ticket before trying again.', invalid: 'Check the required fields, confirmation and review reason.',
  })
}
export function getWorkflow(id: string, signal?: AbortSignal): Promise<WorkflowState> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(id)}/workflow`, { signal })
}
export function updateTicketStatus(id: string, status: TicketStatus, expectedVersion: number): Promise<Ticket> {
  return workflowRequest(`/api/tickets/${encodeURIComponent(id)}/status`, 'PATCH', { status, expected_version: expectedVersion, confirmed: true })
}
export function documentDiscrepancy(id: string, context: string, reason: string): Promise<WorkflowState> {
  return workflowRequest(`/api/tickets/${encodeURIComponent(id)}/discrepancy-resolutions`, 'POST', { context_fingerprint: context, reason, confirmed: true })
}
export function editReplyDraft(ticketId: string, draft: ReplyDraft, content: string, context: string): Promise<ReplyDraft> {
  return workflowRequest(`/api/tickets/${encodeURIComponent(ticketId)}/drafts/${encodeURIComponent(draft.id)}`, 'PATCH', { reply_text: content, expected_version: draft.version ?? 1, context_fingerprint: context })
}
export function reviewReplyDraft(ticketId: string, draft: ReplyDraft, action: 'approve' | 'reject' | 'regenerate', context: string, reason?: string): Promise<ReplyDraft> {
  return workflowRequest(`/api/tickets/${encodeURIComponent(ticketId)}/drafts/${encodeURIComponent(draft.id)}/${action}`, 'POST', { expected_version: draft.version ?? 1, context_fingerprint: context, confirmed: true, ...(action === 'reject' ? { reason } : {}) })
}
export function getDraftRevisions(ticketId: string, draftId: string, signal?: AbortSignal): Promise<DraftRevision[]> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(ticketId)}/drafts/${encodeURIComponent(draftId)}/revisions`, { signal })
}
export function getActivity(ticketId: string, offset = 0, signal?: AbortSignal): Promise<ActivityPage> {
  return ticketRequest(`/api/tickets/${encodeURIComponent(ticketId)}/activity?limit=30&offset=${offset}`, { signal })
}

export type Analytics = {
  generated_at: string; total_tickets: number
  by_category: Record<Category, number>; by_priority: Record<Priority, number>; by_status: Record<TicketStatus, number>
  human_review_tickets: number; draft_decisions: { approved: number; rejected: number }
  volume: { date: string; count: number }[]
  resolution_time: { average_seconds: number | null; measured_tickets: number; unavailable_tickets: number }
}
export function getAnalytics(signal?: AbortSignal): Promise<Analytics> {
  return ticketRequest('/api/analytics', { signal }, { failure: 'Cannot load analytics. Check the backend and retry.' })
}
