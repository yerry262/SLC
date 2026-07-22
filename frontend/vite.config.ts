import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Pinned so repeated local test runs always land on the same port instead
  // of Vite silently incrementing (5173 -> 5174 -> ...) when a stale
  // process is still bound — see CLAUDE.md's "Local Development" section
  // for the kill-and-reuse convention this depends on.
  server: {
    port: 5173,
    strictPort: true,
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
})
