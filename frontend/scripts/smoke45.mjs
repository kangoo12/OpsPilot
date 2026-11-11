// One isolated browser run. A unique seeded sentinel is verified before any writes.
import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium, expect } from '@playwright/test'

const base = 'http://127.0.0.1:5185'
const output = fileURLToPath(new URL('../../.cache/milestone45/', import.meta.url))
const seed = JSON.parse(await readFile(`${output}/seed.json`, 'utf8'))
assert.ok(seed.database.replaceAll('\\', '/').endsWith('/.cache/milestone45/qa.db'))
await mkdir(output, { recursive: true })
process.env.TEMP = output; process.env.TMP = output
const context = await chromium.launchPersistentContext(`${output}/browser-profile`, {
  channel: 'msedge', headless: true, viewport: { width: 1440, height: 1000 },
  args: ['--disable-background-networking', '--disable-component-update'],
})
const result = { passed: false, checks: [], browserErrors: [], generatedDraft: null }
try {
  const sentinelResponse = await context.request.get(`${base}/api/tickets/${seed.target_id}`)
  assert.equal(sentinelResponse.status(), 200, 'Refusing to run against an unrecognized database')
  assert.ok((await sentinelResponse.json()).message.includes(seed.run_id), 'QA sentinel mismatch')
  const initial = await (await context.request.get(`${base}/api/analytics`)).json()
  assert.equal(initial.total_tickets, seed.total)
  assert.deepEqual(initial.draft_decisions, { approved: 1, rejected: 1 })
  const page = await context.newPage()
  page.on('pageerror', error => result.browserErrors.push(error.message))
  page.on('request', request => assert.equal(new URL(request.url()).origin, base))
  await page.goto(base)
  async function listChange(action, predicate) {
    const pending = page.waitForResponse(response => {
      const url = new URL(response.url())
      return url.pathname === '/api/tickets' && response.request().method() === 'GET' && predicate(url.searchParams)
    })
    await action()
    const response = await pending
    assert.equal(response.status(), 200)
    return response.json()
  }
  async function mutation(suffix, action, method = 'POST') {
    const pending = page.waitForResponse(response => response.url().endsWith(suffix) && response.request().method() === method, { timeout: 310000 })
    await action()
    const response = await pending
    const value = await response.json()
    assert.ok(response.ok(), `${response.status()} ${JSON.stringify(value)}`)
    return value
  }
  const nav = page.getByRole('navigation', { name: 'Workspace navigation' })
  await expect(page.getByRole('combobox', { name: 'Sort tickets' })).toBeVisible()
  await listChange(() => page.getByLabel('Search tickets').fill('QA45'), params => params.get('search') === 'QA45')
  await listChange(() => page.getByRole('combobox', { name: 'Category', exact: true }).selectOption('delivery'), params => params.get('category') === 'delivery')
  await listChange(() => page.getByRole('combobox', { name: 'Priority', exact: true }).selectOption('high'), params => params.get('priority') === 'high')
  await listChange(() => page.getByRole('combobox', { name: 'Status', exact: true }).selectOption('new'), params => params.get('status') === 'new')
  const filtered = await listChange(() => page.getByRole('combobox', { name: 'Sort tickets' }).selectOption('oldest'), params => params.get('sort') === 'oldest')
  assert.ok(filtered.items.every(ticket => ticket.category === 'delivery' && ticket.priority === 'high' && ticket.status === 'new'))
  await expect(page.getByText(`${filtered.counts.total} matching tickets`, { exact: true })).toBeVisible()
  await listChange(() => page.getByRole('button', { name: 'Clear filters' }).click(), params => !params.has('category') && !params.has('priority') && !params.has('status'))
  await listChange(() => page.getByRole('combobox', { name: 'Sort tickets' }).selectOption('priority_high'), params => params.get('sort') === 'priority_high')
  await listChange(() => page.getByLabel('Search tickets').fill('DEMO-LAMP-9001'), params => params.get('search') === 'DEMO-LAMP-9001')
  result.checks.push('Combined search/filters/sorting and matching count')
  await page.getByRole('button', { name: `View ticket ${seed.target_id}` }).click()
  await expect(page.getByRole('region', { name: 'Ticket details' }).getByText(seed.target_id, { exact: true })).toBeVisible()
  await page.getByRole('tab', { name: 'Order Details', exact: true }).click()
  await expect(page.getByText('LumaLite desk lamp', { exact: true })).toBeVisible()
  await page.getByRole('tab', { name: 'AI Reply', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Generate suggested reply' })).toBeEnabled()
  const draft = await mutation(`/api/tickets/${seed.target_id}/drafts`, () => page.getByRole('button', { name: 'Generate suggested reply' }).click())
  assert.equal(draft.model, 'qwen3.5:9b')
  result.generatedDraft = draft.reply_text
  await page.getByRole('button', { name: 'Edit reply', exact: true }).click()
  const edit = 'Thank you for your message. Please let us know what further assistance you need.'
  await page.getByLabel('Reply draft content').fill(edit)
  await page.getByRole('tab', { name: 'Overview', exact: true }).click()
  await page.getByRole('tab', { name: 'AI Reply', exact: true }).click()
  await expect(page.getByLabel('Reply draft content')).toHaveValue(edit)
  await nav.getByRole('button', { name: 'Analytics', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Tickets by category' })).toBeVisible()
  await nav.getByRole('button', { name: 'Smart Inbox', exact: true }).click()
  await expect(page.getByLabel('Reply draft content')).toHaveValue(edit)
  const saved = await mutation(`/api/tickets/${seed.target_id}/drafts/${draft.id}`, () => page.getByRole('button', { name: 'Save Draft', exact: true }).click(), 'PATCH')
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: 'Approve', exact: true }).click()
  const approved = await mutation(`/api/tickets/${seed.target_id}/drafts/${draft.id}/approve`, () => page.getByRole('button', { name: 'Confirm approval', exact: true }).click())
  assert.equal(approved.status, 'approved'); assert.equal(approved.reply_text, saved.reply_text)
  const ticket = await (await page.request.get(`${base}/api/tickets/${seed.target_id}`)).json()
  assert.equal(ticket.status, 'new')
  await page.getByRole('tab', { name: 'Activity History', exact: true }).click()
  await expect(page.getByText('Draft approved — nothing sent', { exact: true })).toBeVisible()
  await page.getByRole('tab', { name: 'AI Reply', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Create pending revision', exact: true })).toBeVisible()
  await expect(page.getByTestId('reply-text')).toHaveText(edit)
  await page.screenshot({ path: `${output}/desktop-inbox.png`, fullPage: true })
  result.checks.push('Real local Qwen generation; pending edit preserved across tabs/navigation; approval, activity and ticket status preserved')
  await nav.getByRole('button', { name: 'Analytics', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Draft decisions' })).toContainText('Approved drafts: 2')
  const metrics = await (await page.request.get(`${base}/api/analytics`)).json()
  assert.equal(metrics.total_tickets, seed.total)
  assert.deepEqual(metrics.draft_decisions, { approved: 2, rejected: 1 })
  await page.screenshot({ path: `${output}/desktop-analytics.png`, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('region', { name: 'Ticket volume over time' })).toBeVisible()
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
  await page.screenshot({ path: `${output}/mobile-analytics.png`, fullPage: true })
  await nav.getByRole('button', { name: 'Smart Inbox', exact: true }).click()
  await expect(page.getByTestId('reply-text')).toHaveText(edit)
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
  await page.screenshot({ path: `${output}/mobile-inbox.png`, fullPage: true })
  result.checks.push('Real analytics counts; responsive desktop and mobile layouts without horizontal overflow')
  assert.deepEqual(result.browserErrors, [])
  result.passed = true
} catch (error) {
  result.error = String(error)
  throw error
} finally {
  await writeFile(`${output}/results.json`, JSON.stringify(result, null, 2))
  await context.close()
  console.log(JSON.stringify(result))
}
