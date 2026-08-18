import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_BACKEND_TARGET || 'http://localhost:8000'
  const websocketTarget = backendTarget.replace(/^http/, 'ws')

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': backendTarget,
        '/ws': { target: websocketTarget, ws: true },
      },
    },
  }
})
