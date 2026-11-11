// Read-only follow-up: verify the favicon fix, recovery, and persisted QA state.
// No classification, draft generation or workflow mutation is repeated.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium, expect } from '@playwright/test'

const folder = fileURLToPath(new URL('../../.cache/milestone5d/', import.meta.url))
const base = 'http://127.0.0.1:5195'
const seed = JSON.parse(await readFile(`${folder}/seed.json`,'utf8'))
const prior = JSON.parse(await readFile(`${folder}/browser-results-resumed.json`,'utf8'))
assert.equal(prior.checks.length,7)
process.env.TEMP=folder; process.env.TMP=folder
const context = await chromium.launchPersistentContext(`${folder}/browser-profile-readonly`, {
  channel:'msedge',headless:true,viewport:{width:1440,height:1000},
  args:['--disable-background-networking','--disable-component-update'],
})
const result={passed:false,errors:[],httpErrors:[],checks:[],inducedErrors:[]}
try {
  const response=await context.request.get(`${base}/api/tickets/${seed.conflict_id}`)
  assert.ok(response.ok()); assert.ok((await response.json()).message.includes(seed.run_id))
  const page=await context.newPage(); page.setDefaultTimeout(15000)
  let inducing=false
  page.on('pageerror',e=>result.errors.push(e.message))
  page.on('console',e=>{ if(e.type()==='error') (inducing?result.inducedErrors:result.errors).push(e.text()) })
  page.on('response',r=>{ if(r.status()>=400) (inducing?result.inducedErrors:result.httpErrors).push({path:new URL(r.url()).pathname,status:r.status()}) })
  await page.goto(base)
  await expect(page.getByText('Connected',{exact:true})).toHaveCount(2)
  await expect(page.getByRole('button',{name:`View ticket ${prior.tickets[0].id}`,exact:true})).toBeVisible()
  assert.equal(await page.locator('link[rel="icon"]').getAttribute('href'),'data:,')
  await page.getByRole('button',{name:`View ticket ${prior.tickets[0].id}`,exact:true}).click()
  await page.getByRole('tab',{name:'AI Reply',exact:true}).click()
  await expect(page.getByTestId('reply-text')).toBeVisible()
  const target=prior.tickets[0].id
  const drafts=await (await context.request.get(`${base}/api/tickets/${target}/drafts`)).json()
  assert.equal(drafts.total,3)
  assert.deepEqual(drafts.items.map(d=>d.status).sort(),['approved','pending_review','rejected'])
  assert.equal((await (await context.request.get(`${base}/api/tickets/${target}`)).json()).status,'in_progress')
  result.checks.push('No unsolicited favicon request/error; persisted ticket and three distinct draft decisions')
  assert.deepEqual(result.errors,[]); assert.deepEqual(result.httpErrors,[])
  inducing=true
  await page.route('**/api/tickets?*',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:{message:'Synthetic QA storage outage.'}})}),{times:1})
  await page.getByRole('button',{name:'Refresh tickets',exact:true}).click()
  await expect(page.getByText(/Synthetic QA storage outage/)).toBeVisible()
  await expect(page.getByText(/Showing the last loaded tickets and counts/)).toBeVisible()
  await page.getByRole('button',{name:'Refresh tickets',exact:true}).click()
  await expect(page.getByText(/Synthetic QA storage outage/)).toHaveCount(0)
  await expect(page.getByRole('button',{name:`View ticket ${target}`,exact:true})).toBeVisible()
  inducing=false
  result.checks.push('One explicitly simulated 503 is visible; refresh recovers without losing persisted tickets')
  assert.deepEqual(result.errors,[]); assert.deepEqual(result.httpErrors,[])
  result.passed=true
} finally {
  await writeFile(`${folder}/browser-readonly-followup.json`,JSON.stringify(result,null,2),{flag:'wx'})
  await context.close(); console.log(JSON.stringify(result))
}
