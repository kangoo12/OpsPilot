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
