import { useEffect, useState } from 'react'

// Hash routing, not path routing + a 404.html SPA-fallback rewrite.
//
// Why: GitHub Pages has no server-side rewrites, so a real path route like
// `/rewards` 404s on a hard refresh or a shared link unless a 404.html trick
// redirects it back to index.html. That trick exists once elsewhere in this
// workspace (Spotify-Webapp-Visualizer's public/404.html) but is vestigial
// there — that repo has no router at all (no react-router, no <Route>
// usage), so it isn't actually a proven, load-bearing convention to copy.
// Path routing here would also be the *first* time this repo's Vite `base`
// (currently unset, and this site hasn't deployed yet per CLAUDE.md) gets
// exercised against the real `/SLC/` subpath — two unverified things at
// once. Hash routing sidesteps both: the `#fragment` never reaches the
// server, so GitHub Pages just serves index.html regardless of path depth,
// and it works the same whether or not `base` ever gets set correctly.

function readPath(): string {
  // location.hash includes the leading '#'; strip it and normalize to
  // always start with '/' so route table lookups are exact-match.
  const raw = window.location.hash.slice(1)
  if (!raw || raw === '/') return '/'
  return raw.startsWith('/') ? raw : `/${raw}`
}

/** Current route path (e.g. "/rewards"), kept in sync with location.hash. */
export function useHashRoute(): string {
  const [path, setPath] = useState<string>(readPath)

  useEffect(() => {
    const onHashChange = () => setPath(readPath())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  return path
}
