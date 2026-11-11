// One comprehensive pass against a fresh, independently verified QA database.
import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium, expect } from '@playwright/test'

const base = 'http://127.0.0.1:5195'
const folder = fileURLToPath(new URL('../../.cache/milestone5d/', import.meta.url))
const docs = fileURLToPath(new URL('../../docs/milestone5d/', import.meta.url))
const seed = JSON.parse(await readFile(`${folder}/seed.json`, 'utf8'))
const scenarios = JSON.parse(await readFile(`${docs}/scenarios-v1.json`, 'utf8'))
assert.equal(seed.database, '.cache/milestone5d/browser-qa.db')
await mkdir(folder, { recursive: true })
process.env.TEMP = folder; process.env.TMP = folder
const context = await chromium.launchPersistentContext(`${folder}/${process.argv.includes('--resume') ? 'browser-profile-resume' : 'browser-profile'}`, {
  channel: 'msedge', headless: true, viewport: { width: 1440, height: 1000 },
  args: ['--disable-background-networking', '--disable-component-update'],
})
const resume = process.argv.includes('--resume')
const result = { resumedAfterHarnessLocatorFailure: resume, passed: false, checks: [], browserErrors: [], consoleErrors: [], failedApi: [], requestFailures: [], timings: {}, tickets: [] }
let page
try {
  // The process launch separately verifies the resolved database path. This
  // independent sentinel/row count also proves the browser proxy reaches it.
  const sentinel = await context.request.get(`${base}/api/tickets/${seed.conflict_id}`)
  assert.equal(sentinel.status(), 200)
  assert.ok((await sentinel.json()).message.includes(seed.run_id))
  assert.equal((await (await context.request.get(`${base}/api/analytics`)).json()).total_tickets, seed.total + (resume ? 2 : 0))
  page = await context.newPage()
  page.setDefaultTimeout(15000)
  page.on('pageerror', error => result.browserErrors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') result.consoleErrors.push(message.text()) })
  page.on('requestfailed', request => result.requestFailures.push({ path: new URL(request.url()).pathname, error: request.failure()?.errorText }))
  page.on('response', response => { if (response.status() >= 400 && new URL(response.url()).pathname.startsWith('/api/')) result.failedApi.push({ path:new URL(response.url()).pathname, status:response.status() }) })
  page.on('request', request => assert.equal(new URL(request.url()).origin, base, 'Unexpected external browser request'))
  await page.goto(base)
  await expect(page.getByText('Connected', { exact: true })).toHaveCount(2)
  result.checks.push('Backend/SQLite and local Qwen connectivity visible')
  async function mutation(suffix, action, method = 'POST') {
    const started = Date.now()
    const pending = page.waitForResponse(r => r.url().endsWith(suffix) && r.request().method() === method, { timeout:310000 })
    pending.catch(() => {}) // Avoid unhandled rejection if a locator fails first.
    await action()
    const response = await pending
    const value = await response.json()
    assert.ok(response.ok(), `${response.status()} ${JSON.stringify(value)}`)
    result.timings[`${method} ${suffix}`] = (Date.now()-started)/1000
    return value
  }
  async function listChange(action, predicate) {
    const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/tickets' && r.request().method() === 'GET' && predicate(new URL(r.url()).searchParams))
    pending.catch(() => {}) // Avoid unhandled rejection if a locator fails first.
    await action()
    const response = await pending; assert.equal(response.status(),200)
    return response.json()
  }
  const nav = page.getByRole('navigation',{name:'Workspace navigation'})
  if (!resume) {
  await page.getByRole('button',{name:'New customer message',exact:true}).click()
  for (const language of ['english','greek']) {
    await page.getByLabel('Customer message',{exact:true}).fill(scenarios.browser[language])
    const ticket = await mutation('/api/tickets', async () => {
      await page.getByRole('button',{name:'Classify & save ticket',exact:true}).click()
      await expect(page.getByRole('button',{name:'Classifying locally…',exact:true})).toBeDisabled()
    })
    assert.equal(ticket.category,'delivery'); assert.equal(ticket.priority,'medium')
    assert.equal(ticket.order_id,language === 'english' ? 'DEMO-LAMP-9001' : 'GR-1045')
    result.tickets.push(ticket)
    await expect(page.getByRole('region',{name:'Ticket details'}).getByText(ticket.id,{exact:true})).toBeVisible()
  }
  } else {
    const saved = await (await context.request.get(`${base}/api/tickets?limit=100`)).json()
    for (const language of ['english','greek']) {
      const matches = saved.items.filter(t => t.message === scenarios.browser[language])
      assert.equal(matches.length,1); assert.equal(matches[0].category,'delivery'); assert.equal(matches[0].priority,'medium')
      result.tickets.push(matches[0])
    }
  }
  result.checks.push('English/Greek UI submissions and loading passed before locator failure; exact saved tickets verified on resume')
  const total = seed.total + 2
  const second = await listChange(() => page.getByRole('button',{name:'Next',exact:true}).click(), p => p.get('offset') === '20')
  assert.equal(second.items.length,6); assert.equal(second.counts.total,total)
  const filtered = await listChange(() => page.getByRole('combobox',{name:'Category',exact:true}).selectOption('delivery'), p => p.get('category') === 'delivery' && p.get('offset') === '0')
  assert.equal(filtered.counts.total,2)
  await listChange(() => page.getByRole('combobox',{name:'Priority',exact:true}).selectOption('medium'), p => p.get('priority') === 'medium')
  await listChange(() => page.getByRole('combobox',{name:'Status',exact:true}).selectOption('new'), p => p.get('status') === 'new')
  const found = await listChange(() => page.getByLabel('Search tickets').fill('DEMO-LAMP-9001'), p => p.get('search') === 'DEMO-LAMP-9001')
  assert.equal(found.counts.total,1)
  await listChange(() => page.getByRole('button',{name:'Clear filters',exact:true}).click(), p => !p.has('category') && !p.has('priority') && !p.has('status'))
  await listChange(() => page.getByRole('button',{name:'Clear search',exact:true}).click(), p => !p.has('search'))
  const oldest = await listChange(() => page.getByRole('combobox',{name:'Sort tickets'}).selectOption('oldest'), p => p.get('sort') === 'oldest')
  assert.ok(oldest.items.every((t,i) => !i || t.created_at >= oldest.items[i-1].created_at))
  const ranked = await listChange(() => page.getByRole('combobox',{name:'Sort tickets'}).selectOption('priority_high'), p => p.get('sort') === 'priority_high')
  const ranks = {urgent:3,high:2,medium:1,low:0}
  assert.ok(ranked.items.every((t,i) => !i || ranks[t.priority] <= ranks[ranked.items[i-1].priority]))
  result.checks.push('Pagination, reset, combined search/filters, matching counts, oldest and priority sorting')
  await listChange(() => page.getByLabel('Search tickets').fill('unique-no-match-5d'), p => p.get('search') === 'unique-no-match-5d')
  await expect(page.getByText('No results found.',{exact:false})).toBeVisible()
  await listChange(() => page.getByLabel('Search tickets').fill('DEMO-LAMP-9001'), p => p.get('search') === 'DEMO-LAMP-9001')
  const target = result.tickets[0]
  await page.getByRole('button',{name:`View ticket ${target.id}`,exact:true}).click()
  await page.getByRole('tab',{name:'Order Details',exact:true}).click()
  await expect(page.getByText('LumaLite desk lamp',{exact:true})).toBeVisible()
  await page.getByRole('tab',{name:'AI Reply',exact:true}).click()
  const draft = await mutation(`/api/tickets/${target.id}/drafts`, async () => {
    await page.getByRole('button',{name:'Generate suggested reply',exact:true}).click()
    await expect(page.getByRole('button',{name:'Generating locally…',exact:true})).toBeDisabled()
  })
  assert.equal(draft.status,'pending_review'); result.generatedDraft = draft.reply_text
  assert.ok(draft.reply_text.includes('2026-11-14'))
  await page.getByRole('button',{name:'Edit reply',exact:true}).click()
  const edit = `${draft.reply_text}\n\nPlease let us know if you need further clarification.`
  await page.getByLabel('Reply draft content').fill(edit)
  await page.getByRole('tab',{name:'Overview',exact:true}).click()
  await page.getByRole('tab',{name:'AI Reply',exact:true}).click()
  await expect(page.getByLabel('Reply draft content')).toHaveValue(edit)
  const saved = await mutation(`/api/tickets/${target.id}/drafts/${draft.id}`, () => page.getByRole('button',{name:'Save Draft',exact:true}).click(), 'PATCH')
  await page.getByRole('button',{name:'Approve',exact:true}).click()
  const approved = await mutation(`/api/tickets/${target.id}/drafts/${draft.id}/approve`, () => page.getByRole('button',{name:'Confirm approval',exact:true}).click())
  assert.equal(approved.reply_text,saved.reply_text); assert.equal(approved.status,'approved')
  await expect(page.getByRole('button',{name:'Approve',exact:true})).toBeDisabled()
  await page.getByRole('button',{name:'Create pending revision',exact:true}).click()
  await page.getByLabel('Reply draft content').fill(`${edit}\n\nThank you for checking the details.`)
  const child = await mutation(`/api/tickets/${target.id}/drafts/${draft.id}`, () => page.getByRole('button',{name:'Save as pending revision',exact:true}).click(), 'PATCH')
  assert.notEqual(child.id,draft.id); assert.equal(child.parent_draft_id,draft.id); assert.equal(child.status,'pending_review')
  const allDrafts = await (await page.request.get(`${base}/api/tickets/${target.id}/drafts`)).json()
  assert.equal(allDrafts.items.find(d => d.id === draft.id).reply_text,edit)
  assert.equal(allDrafts.items.find(d => d.id === draft.id).status,'approved')
  await page.getByRole('button',{name:'Reject',exact:true}).click()
  await page.getByLabel('Rejection reason').fill('Synthetic audit revision is redundant; retain the approved original.')
  const rejected = await mutation(`/api/tickets/${target.id}/drafts/${child.id}/reject`, () => page.getByRole('button',{name:'Confirm rejection',exact:true}).click())
  assert.equal(rejected.status,'rejected')
  await page.getByRole('button',{name:'Regenerate',exact:true}).click()
  const regenerated = await mutation(`/api/tickets/${target.id}/drafts/${child.id}/regenerate`, () => page.getByRole('button',{name:'Confirm regeneration',exact:true}).click())
  assert.equal(regenerated.status,'pending_review'); assert.equal(regenerated.parent_draft_id,child.id)
  await page.getByText('Draft revision history',{exact:true}).click()
  await expect(page.getByText(/Revision 1 · created/)).toBeVisible()
  await page.getByRole('tab',{name:'Overview',exact:true}).click()
  await page.getByRole('combobox',{name:'Ticket status',exact:true}).selectOption('in_progress')
  await page.getByRole('button',{name:'Update status',exact:true}).click()
  await mutation(`/api/tickets/${target.id}/status`, () => page.getByRole('button',{name:'Confirm status change',exact:true}).click(), 'PATCH')
  await page.getByRole('tab',{name:'Activity History',exact:true}).click()
  await expect(page.getByText('Draft approved — nothing sent',{exact:true})).toBeVisible()
  await expect(page.getByText('Ticket status changed',{exact:true})).toBeVisible()
  await expect(page.getByText('AI draft regenerated',{exact:true})).toBeVisible()
  result.checks.push('Grounded real Qwen draft, edit, approval, immutable parent, pending child, rejection, real regeneration, status, audit and revision history')
  await page.getByRole('button',{name:`View ticket ${seed.conflict_id}`,exact:true}).click()
  for (const tab of ['Overview','Order Details','AI Reply','Activity History']) {
    await page.getByRole('tab',{name:tab,exact:true}).click()
    await expect(page.getByRole('alert',{name:'Order consistency warning'})).toBeVisible()
  }
  result.checks.push('Material human-review warning remains visible in all workspace tabs')
  await listChange(() => page.getByLabel('Search tickets').fill('window.auditXss'), p => p.get('search') === 'window.auditXss')
  await page.getByRole('button',{name:`View ticket ${seed.xss_id}`,exact:true}).click()
  await expect(page.getByRole('region',{name:'Ticket details'})).toContainText('<script>window.auditXss=1</script>')
  assert.equal(await page.evaluate(() => window.auditXss),undefined)
  result.checks.push('Untrusted HTML/script fixture renders as literal text, without execution')
  await nav.getByRole('button',{name:'Analytics',exact:true}).click()
  await expect(page.getByRole('region',{name:'Draft decisions'})).toContainText('Approved drafts: 1')
  const metrics = await (await page.request.get(`${base}/api/analytics`)).json()
  assert.equal(metrics.total_tickets,total)
  assert.deepEqual(metrics.draft_decisions,{approved:1,rejected:1})
  assert.deepEqual(metrics.by_status,{new:25,in_progress:1,waiting_for_customer:0,resolved:0})
  assert.equal(metrics.by_category.delivery,2)
  result.analytics = metrics
  for (const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
    await page.setViewportSize({width,height})
    for (const section of ['Analytics','Smart Inbox']) {
      await nav.getByRole('button',{name:section,exact:true}).click()
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1),`${name}/${section} overflow`)
      await page.screenshot({path:`${folder}/${name}-${section.replaceAll(' ','-')}.png`,fullPage:true})
    }
  }
  await page.reload()
  await expect(page.getByText('Connected',{exact:true})).toHaveCount(2)
  const persisted = await (await page.request.get(`${base}/api/tickets/${target.id}`)).json()
  assert.equal(persisted.status,'in_progress')
  const stored = await (await page.request.get(`${base}/api/tickets/${target.id}/drafts`)).json()
  assert.equal(stored.total,3); assert.equal(stored.items.find(d => d.id===draft.id).reply_text,edit)
  await page.getByRole('button',{name:`View ticket ${target.id}`,exact:true}).click()
  await page.getByRole('tab',{name:'AI Reply',exact:true}).click()
  await expect(page.getByTestId('reply-text')).toHaveText(regenerated.reply_text)
  result.checks.push('Analytics reflects QA rows/decisions; desktop/mobile no overflow; reload preserves ticket and all three drafts')
  assert.deepEqual(result.browserErrors,[]); assert.deepEqual(result.failedApi,[])
  assert.deepEqual(result.consoleErrors,[])
  result.passed = true
} catch (error) {
  result.error = String(error)
  if (page) await page.screenshot({path:`${folder}/failure.png`,fullPage:true}).catch(() => {})
  throw error
} finally {
  await writeFile(`${folder}/${resume ? 'browser-results-resumed' : 'browser-results'}.json`,JSON.stringify(result,null,2),{flag:'wx'})
  await context.close()
  console.log(JSON.stringify(result,null,2))
}
