// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import App from './App'
import { checkConnection, getAnalytics, getTicket, listTickets, type Ticket } from './api'

vi.mock('./api', async () => ({ ...await vi.importActual<typeof import('./api')>('./api'), checkConnection: vi.fn(), getAnalytics: vi.fn(), getTicket: vi.fn(), listTickets: vi.fn() }))
vi.mock('./TicketSupport', () => ({ default: () => <label>Retained draft<input defaultValue="Unsaved draft" /></label> }))
afterEach(() => { cleanup(); vi.resetAllMocks() })

it('preserves selected ticket and workspace state between Inbox and Analytics', async () => {
  const ticket: Ticket = { id: 'ticket-1', message: 'Where is my order?', category: 'delivery', priority: 'medium', order_id: null, customer_intent: 'Locate parcel', reason: 'Delayed parcel', status: 'new', created_at: '2026-11-11T12:00:00Z' }
  vi.mocked(checkConnection).mockResolvedValue({ state: 'connected', message: 'Ready' })
  vi.mocked(listTickets).mockResolvedValue({ items: [ticket], counts: { total: 1, new: 1, high: 0, urgent: 0 }, limit: 20, offset: 0 })
  vi.mocked(getTicket).mockResolvedValue(ticket)
  vi.mocked(getAnalytics).mockRejectedValue(new Error('offline'))
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'View ticket ticket-1' }))
  const editor = await screen.findByLabelText('Retained draft')
  fireEvent.change(editor, { target: { value: 'Keep my pending edit' } })
  const navigation = screen.getByRole('navigation', { name: 'Workspace navigation' })
  fireEvent.click(within(navigation).getByRole('button', { name: 'Analytics' }))
  await screen.findByRole('alert')
  expect(screen.queryByLabelText('Retained draft')?.closest('[hidden]')).toBeTruthy()
  fireEvent.click(within(navigation).getByRole('button', { name: 'Smart Inbox' }))
  expect((screen.getByLabelText('Retained draft') as HTMLInputElement).value).toBe('Keep my pending edit')
  expect(screen.getByRole('button', { name: 'View ticket ticket-1' }).getAttribute('aria-pressed')).toBe('true')
  expect(getTicket).toHaveBeenCalledTimes(1)
})
