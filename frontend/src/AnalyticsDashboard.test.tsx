// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import AnalyticsDashboard from './AnalyticsDashboard'
import { getAnalytics, type Analytics } from './api'

vi.mock('./api', async () => ({ ...await vi.importActual<typeof import('./api')>('./api'), getAnalytics: vi.fn() }))
const empty: Analytics = {
  generated_at: '2026-11-11T12:00:00Z', total_tickets: 0,
  by_category: { delivery: 0, returns: 0, payments: 0, technical_support: 0, other: 0 },
  by_priority: { low: 0, medium: 0, high: 0, urgent: 0 },
  by_status: { new: 0, in_progress: 0, waiting_for_customer: 0, resolved: 0 },
  human_review_tickets: 0, draft_decisions: { approved: 0, rejected: 0 },
  volume: [{ date: '2026-11-11', count: 0 }], resolution_time: { average_seconds: null, measured_tickets: 0, unavailable_tickets: 0 },
}
beforeEach(() => { vi.resetAllMocks(); vi.mocked(getAnalytics).mockResolvedValue(empty) })
afterEach(cleanup)

it('shows loading, empty data and unavailable resolution time honestly', async () => {
  render(<AnalyticsDashboard active />)
  expect(screen.getByText('Loading analytics…')).toBeTruthy()
  await screen.findByText(/No tickets yet/)
  expect(screen.getByText('Not available yet')).toBeTruthy()
  expect(screen.getByRole('region', { name: 'Ticket volume over time' })).toBeTruthy()
})

it('shows real metric values and accessible breakdowns', async () => {
  vi.mocked(getAnalytics).mockResolvedValue({ ...empty, total_tickets: 7, by_category: { ...empty.by_category, delivery: 7 },
    draft_decisions: { approved: 3, rejected: 2 }, resolution_time: { average_seconds: 7200, measured_tickets: 2, unavailable_tickets: 1 } })
  render(<AnalyticsDashboard active />)
  await screen.findByText('2.0 hours')
  expect(within(screen.getByRole('region', { name: 'Tickets by category' })).getByText('7')).toBeTruthy()
  expect(screen.getByRole('region', { name: 'Draft decisions' }).textContent).toContain('Approved drafts: 3')
  expect(screen.queryByText(/No tickets yet/)).toBeNull()
})

it('reports errors and retries without fabricated metrics', async () => {
  vi.mocked(getAnalytics).mockRejectedValueOnce(new Error('offline'))
  render(<AnalyticsDashboard active />)
  expect((await screen.findByRole('alert')).textContent).toContain('Cannot load analytics')
  expect(screen.queryByRole('region', { name: 'Draft decisions' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Refresh analytics' }))
  await screen.findByText(/No tickets yet/)
  expect(getAnalytics).toHaveBeenCalledTimes(2)
})

it('loads only when active and ignores obsolete navigation responses', async () => {
  const view = render(<AnalyticsDashboard active={false} />)
  expect(getAnalytics).not.toHaveBeenCalled()
  let finish!: (value: Analytics) => void
  vi.mocked(getAnalytics).mockReturnValueOnce(new Promise(resolve => { finish = resolve }))
  view.rerender(<AnalyticsDashboard active />)
  const signal = vi.mocked(getAnalytics).mock.calls[0][0]!
  view.rerender(<AnalyticsDashboard active={false} />)
  expect(signal.aborted).toBe(true)
  view.rerender(<AnalyticsDashboard active />)
  await screen.findByText(/No tickets yet/)
  await act(async () => { finish({ ...empty, total_tickets: 100 }) })
  expect(screen.getByText(/No tickets yet/)).toBeTruthy()
})
