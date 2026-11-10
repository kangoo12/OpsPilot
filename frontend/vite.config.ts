import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const envDir = fileURLToPath(new URL('..', import.meta.url))
  const env = loadEnv(mode, envDir, '')
  const backend = env.BACKEND_URL || 'http://127.0.0.1:8000'
  const url = new URL(backend)
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw new Error('BACKEND_URL must be an HTTP loopback URL')
  }
  return {
    envDir,
    plugins: [react(), tailwindcss()],
    server: { proxy: { '/api': { target: backend, changeOrigin: true, proxyTimeout: 315000 } } },
    preview: { proxy: { '/api': { target: backend, changeOrigin: true, proxyTimeout: 315000 } } },
  }
})
