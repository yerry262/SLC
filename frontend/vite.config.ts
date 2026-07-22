import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// This is a GitHub Pages *project* site, served from a subpath
// (https://yerry262.github.io/SLC/), not domain root. Without `base` set,
// Vite emits absolute-root asset paths in index.html (e.g.
// `/assets/index-xyz.js`), which resolve to
// `https://yerry262.github.io/assets/index-xyz.js` under Pages — missing
// the `/SLC/` prefix, a 404. `base: '/SLC/'` fixes that.
//
// Scoped to production build (+ `vite preview`, which serves that same
// build output) via the conditional-config function form, NOT applied
// unconditionally — `base` affects the dev server's own path too, and
// this repo's local dev is pinned to serve from `/` at localhost:5173
// (see CLAUDE.md's "Local Development" section). Hardcoded literal rather
// than sourced from an env var: this is a single, fixed deployment target
// (one repo name, one Pages URL, no staging/custom-domain variant), so
// there's no real multi-environment need an env var would serve — Vite's
// own GitHub Pages deployment guide recommends exactly this literal
// `base: '/<REPO>/'` form.
export default defineConfig(({ command, isPreview }) => ({
  plugins: [react()],
  base: command === 'build' || isPreview ? '/SLC/' : '/',
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
}))
