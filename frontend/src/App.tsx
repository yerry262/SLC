import { NavBar } from './components/NavBar'
import { useHashRoute } from './routing/useHashRoute'
import { routes, defaultRoute } from './routing/routes'
import './App.css'

function App() {
  const path = useHashRoute()
  // Unknown/stale hash (e.g. an old bookmark) falls back to Dashboard
  // rather than a 404 — there's no server involved to 404 against anyway.
  const route = routes.find((r) => r.path === path) ?? defaultRoute

  return (
    <div className="app-shell">
      <NavBar routes={routes} currentPath={route.path} />
      <main className="app-shell__main">{route.element}</main>
    </div>
  )
}

export default App
