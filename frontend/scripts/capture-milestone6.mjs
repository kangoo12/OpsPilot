// Read-only portfolio capture against the isolated 5D synthetic QA snapshot.
import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium, expect } from '@playwright/test'

const base = 'http://127.0.0.1:5196'
const local = fileURLToPath(new URL('../../.cache/milestone6/', import.meta.url))
const output = fileURLToPath(new URL('../../docs/milestone6/screenshots/', import.meta.url))
const seed = JSON.parse(await readFile(new URL('../../.cache/milestone5d/seed.json', import.meta.url), 'utf8'))
const prior = JSON.parse(await readFile(new URL('../../.cache/milestone5d/browser-results-resumed.json', import.meta.url), 'utf8'))
await mkdir(output, { recursive: true })
process.env.TEMP = local; process.env.TMP = local
const context = await chromium.launchPersistentContext(`${local}/capture-profile`, {
  channel: 'msedge', headless: true, viewport: { width: 1440, height: 1100 },
  args: ['--disable-background-networking', '--disable-component-update'],
})
const result = { viewport: { width: 1440, height: 1100 }, inferenceCalls: 0, apiMutations: 0, screenshots: [], pageErrors: [], apiErrors: [] }
try {
  const sentinel = await context.request.get(`${base}/api/tickets/${seed.conflict_id}`)
  assert.equal(sentinel.status(), 200)
  assert.ok((await sentinel.json()).message.includes(seed.run_id))
  const target = prior.tickets[0].id
  const page = await context.newPage(); page.setDefaultTimeout(15000)
  page.on('pageerror', error => result.pageErrors.push(error.message))
  page.on('response', response => { if (response.status() >= 400 && new URL(response.url()).pathname.startsWith('/api/')) result.apiErrors.push(response.status()) })
  page.on('request', request => {
    assert.equal(new URL(request.url()).origin, base)
    assert.equal(request.method(), 'GET', 'Capture must never mutate data or request inference')
  })
  await page.goto(base)
  await expect(page.getByText('Connected', { exact: true })).toHaveCount(2)
  // Filter existing fixtures through the actual UI; do not alter rendered content.
  await page.getByRole('combobox', { name: 'Category', exact: true }).selectOption('delivery')
  await expect(page.getByText('2 matching tickets', { exact: true })).toBeVisible()
  async function capture(name) {
    await page.screenshot({ path: `${output}/${name}.png`, animations: 'disabled' })
    result.screenshots.push(`docs/milestone6/screenshots/${name}.png`)
  }
  await capture('01-overview')
  await page.getByRole('button', { name: `View ticket ${target}`, exact: true }).click()
  await expect(page.getByRole('region', { name: 'Ticket details' })).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Ticket status', exact: true })).toBeEnabled()
  await capture('02-smart-inbox')
  await page.getByRole('tab', { name: 'Order Details', exact: true }).click()
  await expect(page.getByText('LumaLite desk lamp', { exact: true })).toBeVisible()
  await page.getByRole('tablist', { name: 'Ticket workspace' }).scrollIntoViewIfNeeded()
  await capture('03-order-verification')
  await page.getByRole('tab', { name: 'AI Reply', exact: true }).click()
  await expect(page.getByTestId('reply-text')).toBeVisible()
  await page.getByTestId('reply-text').scrollIntoViewIfNeeded()
  await capture('04-draft-review')
  await page.getByRole('navigation', { name: 'Workspace navigation' }).getByRole('button', { name: 'Analytics', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Draft decisions' })).toContainText('Approved drafts: 1')
  await page.evaluate(() => window.scrollTo(0, 0))
  await capture('05-analytics')
  assert.deepEqual(result.pageErrors, []); assert.deepEqual(result.apiErrors, [])
  const record = process.argv.includes('--refresh') ? 'capture-result-refreshed.json' : 'capture-result.json'
  await writeFile(`${local}/${record}`, JSON.stringify(result, null, 2), { flag: 'wx' })
  console.log(JSON.stringify(result))
} finally { await context.close() }
