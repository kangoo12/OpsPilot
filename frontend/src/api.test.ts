import { afterEach, describe, expect, it, vi } from 'vitest'
import { checkConnection } from './api'

afterEach(() => { vi.unstubAllGlobals() })

function respond(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
  }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('connection checks', () => {
  it('reports backend and SQLite health', async () => {
    const fetchMock = respond({ status: 'ok', database: 'connected' })
    expect((await checkConnection('backend')).state).toBe('connected')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/health')
  })

  it('reports the actual model returned by the backend', async () => {
    respond({ status: 'ok', model: 'qwen3.5:9b', message: 'Ready' })
    expect(await checkConnection('ollama')).toEqual({ state: 'connected', model: 'qwen3.5:9b', message: 'Ready' })
  })

  it('preserves actionable missing-model messages on HTTP 503', async () => {
    respond({ status: 'model_missing', model: 'qwen3.5:9b', message: 'Model is not installed' }, 503)
    expect(await checkConnection('ollama')).toMatchObject({ state: 'error', message: 'Model is not installed' })
  })

  it('does not report a failed HTTP response as connected', async () => {
    respond({ status: 'ok', database: 'connected' }, 503)
    expect((await checkConnection('backend')).state).toBe('error')
  })

  it('handles an unavailable backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    expect(await checkConnection('backend')).toMatchObject({ state: 'error', message: expect.stringContaining('Start the API') })
    expect((await checkConnection('ollama')).state).toBe('error')
  })

  it('handles an unexpected proxy response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Error</html>')))
    expect((await checkConnection('backend')).state).toBe('error')
  })

  it('rejects malformed AI health data', async () => {
    respond({ status: 'ok' })
    expect((await checkConnection('ollama')).state).toBe('error')
  })
})
