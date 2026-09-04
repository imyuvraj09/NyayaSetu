import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // SPA fallback: serve index.html for all non-asset routes (e.g. /about)
    historyApiFallback: true,
  },
})
