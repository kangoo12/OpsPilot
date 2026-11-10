// Requires isolated QA servers. Creates synthetic tickets, never targets the demo DB.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium, expect } from '@playwright/test'

const base = new URL(process.env.OPSPILOT_SMOKE_URL || 'http://127.0.0.1:5180')
assert.ok(base.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(base.hostname))
assert.equal(base.port, '5180', 'Milestone 3B smoke must use isolated QA port 5180')
const output = fileURLToPath(new URL('../../.cache/smoke3b/', import.meta.url))
await mkdir(output, { recursive: true })
process.env.TEMP = output; process.env.TMP = output
const context = await chromium.launchPersistentContext(`${output}/browser-profile`, { channel: 'msedge', headless: true,
  viewport: { width: 1440, height: 1100 }, args: ['--disable-background-networking', '--disable-component-update'] })
const result = { tickets: [], drafts: [], checks: [], browserErrors: [] }
const checkpoint = async () => writeFile(`${output}/results.json`, JSON.stringify(result, null, 2))
try {
  const page = await context.newPage()
  const health = await (await page.request.get(new URL('/api/health', base).href)).json()
  assert.equal(health.isolated_qa, true, 'Refusing to run: backend is not using data/milestone3b-qa.db')
  page.on('pageerror', error => result.browserErrors.push(error.message))
  page.on('request', request => assert.equal(new URL(request.url()).origin, base.origin))
  await page.goto(base.href)
  async function waitResponse(suffix, method, action) {
    const pending = page.waitForResponse(response => response.url().endsWith(suffix) && response.request().method() === method, { timeout: 310000 })
    await action()
    const response = await pending
    const value = await response.json()
    assert.ok(response.ok(), `${response.status()} ${JSON.stringify(value)}`)
    return value
  }
  async function create(message) {
    await page.getByLabel('Customer message', { exact: true }).fill(message)
    const ticket = await waitResponse('/api/tickets', 'POST', () => page.getByRole('button', { name: 'Classify & save ticket' }).click())
    result.tickets.push(ticket)
    await expect(page.getByRole('region', { name: 'Ticket details' }).getByText(ticket.id, { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate suggested reply' })).toBeEnabled()
    return ticket
  }
  async function generate(ticket) {
    const draft = await waitResponse(`/api/tickets/${ticket.id}/drafts`, 'POST', () => page.getByRole('button', { name: 'Generate suggested reply' }).click())
    result.drafts.push(draft); await checkpoint()
    await expect(page.getByTestId('reply-text')).toHaveText(draft.reply_text)
    return draft
  }
  async function confirmAction(name, confirmName, suffix, method = 'POST') {
    await expect(page.getByRole('button', { name, exact: true })).toBeEnabled()
    await page.getByRole('button', { name, exact: true }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    return waitResponse(suffix, method, () => page.getByRole('button', { name: confirmName, exact: true }).click())
  }
  async function status(ticket, target) {
    await page.getByLabel('Ticket status').selectOption(target)
    const name = target === 'in_progress' && (await page.getByRole('button', { name: 'Reopen ticket' }).count()) ? 'Reopen ticket' : 'Update status'
    const updated = await confirmAction(name, 'Confirm status change', `/api/tickets/${ticket.id}/status`, 'PATCH')
    assert.equal(updated.status, target)
    await expect(page.getByLabel('Ticket status')).toHaveValue(target)
    result.checks.push(`ticket status ${target}`)
  }
  const ticket = await create('Where is my order #DEMO-LAMP-9001? Please provide the recorded delivery estimate.')
  const draft = await generate(ticket)
  await page.getByRole('button', { name: 'Edit reply', exact: true }).click()
  const editedText = 'Thank you for your message. Please let us know what additional help you need with this order.'
  await page.getByLabel('Reply draft content').fill(editedText)
  const saved = await waitResponse(`/api/tickets/${ticket.id}/drafts/${draft.id}`, 'PATCH', () => page.getByRole('button', { name: 'Save Draft', exact: true }).click())
  assert.equal(saved.version, 2); assert.equal(saved.original_content, draft.reply_text)
  await expect(page.getByTestId('reply-text')).toHaveText(editedText)
  const approved = await confirmAction('Approve', 'Confirm approval', `/api/tickets/${ticket.id}/drafts/${draft.id}/approve`)
  assert.equal(approved.status, 'approved')
  assert.equal((await (await page.request.get(new URL(`/api/tickets/${ticket.id}`, base).href)).json()).status, 'new')
  await expect(page.getByRole('region', { name: 'AI suggested reply' }).getByText('Approved', { exact: true })).toBeVisible()
  await page.screenshot({ path: `${output}/approved.png`, fullPage: true })
  result.drafts.push(approved)

  await page.getByRole('button', { name: 'Create pending revision' }).click()
  await page.getByLabel('Reply draft content').fill('Thank you. Please confirm what additional information you need about the order.')
  const child = await waitResponse(`/api/tickets/${ticket.id}/drafts/${draft.id}`, 'PATCH', () => page.getByRole('button', { name: 'Save as pending revision' }).click())
  assert.notEqual(child.id, draft.id); assert.equal(child.parent_draft_id, approved.id); assert.equal(child.status, 'pending_review')
  let all = await (await page.request.get(new URL(`/api/tickets/${ticket.id}/drafts`, base).href)).json()
  assert.equal(all.items.find(item => item.id === approved.id).reply_text, editedText)
  assert.equal(all.items.find(item => item.id === approved.id).status, 'approved')
  await page.getByRole('button', { name: 'Reject', exact: true }).click()
  await page.getByRole('button', { name: 'Confirm rejection' }).click()
  await expect(page.getByRole('dialog')).toContainText('rejection reason')
  await page.getByLabel('Rejection reason').fill('Needs a clearer explanation of the recorded estimate.')
  const rejected = await waitResponse(`/api/tickets/${ticket.id}/drafts/${child.id}/reject`, 'POST', () => page.getByRole('button', { name: 'Confirm rejection' }).click())
  assert.equal(rejected.status, 'rejected'); assert.ok(rejected.rejected_at && rejected.reviewer)
  const regenerated = await confirmAction('Regenerate', 'Confirm regeneration', `/api/tickets/${ticket.id}/drafts/${child.id}/regenerate`)
  assert.notEqual(regenerated.id, child.id); assert.equal(regenerated.parent_draft_id, child.id)
  result.drafts.push(child, rejected, regenerated)
  for (const target of ['in_progress', 'waiting_for_customer', 'resolved', 'in_progress']) await status(ticket, target)
  await page.getByText('Activity History', { exact: true }).click()
  await expect(page.getByText('Draft approved — nothing sent', { exact: true })).toBeVisible()
  result.checks.push('approved content unchanged; child revision; rejection reason; regeneration; activity timeline')

  const conflict = await create("My smartphone from order #DEMO-LAMP-9001 was delivered today, but it won't turn on.")
  const neutral = await generate(conflict)
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeDisabled()
  let workflow = await (await page.request.get(new URL(`/api/tickets/${conflict.id}/workflow`, base).href)).json()
  const bypass = await page.request.post(new URL(`/api/tickets/${conflict.id}/drafts/${neutral.id}/approve`, base).href, { data: { expected_version: neutral.version, context_fingerprint: workflow.context_fingerprint, confirmed: true } })
  assert.equal(bypass.status(), 409)
  await page.getByRole('button', { name: 'Document human review' }).click()
  const reviewReason = 'Compared both sources; approve only the neutral clarification request and ask for the correct product and order reference.'
  await page.getByLabel('Human review reason').fill(reviewReason)
  await waitResponse(`/api/tickets/${conflict.id}/discrepancy-resolutions`, 'POST', () => page.getByRole('button', { name: 'Confirm documentation' }).click())
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeEnabled()
  const reviewed = await confirmAction('Approve', 'Confirm approval', `/api/tickets/${conflict.id}/drafts/${neutral.id}/approve`)
  assert.equal(reviewed.status, 'approved')
  await expect(page.getByRole('alert', { name: 'Order consistency warning' })).toBeVisible()
  await expect(page.getByText(reviewReason, { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Create pending revision' }).click()
  await page.getByLabel('Reply draft content').fill('Your LumaLite desk lamp is in transit. We have refunded your payment.')
  const unsafe = await waitResponse(`/api/tickets/${conflict.id}/drafts/${neutral.id}`, 'PATCH', () => page.getByRole('button', { name: 'Save as pending revision' }).click())
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeDisabled()
  workflow = await (await page.request.get(new URL(`/api/tickets/${conflict.id}/workflow`, base).href)).json()
  const stillBlocked = await page.request.post(new URL(`/api/tickets/${conflict.id}/drafts/${unsafe.id}/approve`, base).href, { data: { expected_version: unsafe.version, context_fingerprint: workflow.context_fingerprint, confirmed: true } })
  assert.equal(stillBlocked.status(), 409)
  result.drafts.push(reviewed, unsafe)
  result.checks.push('unresolved discrepancy API blocked; human reason persisted; warning remains; unsupported edited claims still blocked')
  await page.reload()
  await page.getByRole('button', { name: `View ticket ${conflict.id}` }).click()
  await expect(page.getByLabel('Saved drafts')).toBeVisible()
  await page.getByLabel('Saved drafts').selectOption(reviewed.id)
  await expect(page.getByTestId('reply-text')).toHaveText(neutral.reply_text)
  await expect(page.getByText(reviewReason, { exact: true })).toBeVisible()
  await page.screenshot({ path: `${output}/desktop.png`, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
  await page.screenshot({ path: `${output}/mobile.png`, fullPage: true })
  const history = await (await page.request.get(new URL(`/api/tickets/${conflict.id}/activity?limit=100`, base).href)).json()
  result.activity = history
  assert.ok(history.items.some(item => item.event_type === 'discrepancy_documented' && item.actor === 'Local Operator'))
  assert.deepEqual(result.browserErrors, [])
  result.passed = true
  await checkpoint()
  console.log(JSON.stringify({ passed: true, tickets: result.tickets.map(item => item.id), checks: result.checks, activityEvents: history.total, browserErrors: result.browserErrors }))
} finally {
  await context.close()
}
