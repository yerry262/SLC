import type { RouteConfig } from '../routing/routes'
import './NavBar.css'

interface NavBarProps {
  routes: RouteConfig[]
  currentPath: string
}

// Persistent top nav — the new home for the "button per section" shape of
// the old dashboard's Main_Menu.ipynb (button_notebooks), now backed by
// real hash routing instead of `%run`-into-an-Output-widget. Plain anchors
// with `href="#/path"` rather than click handlers: works with cmd/ctrl-click
// and "open in new tab", is keyboard-tabbable, and browser back/forward
// already works for free via `hashchange`.
export function NavBar({ routes, currentPath }: NavBarProps) {
  return (
    <header className="nav-bar">
      <a className="nav-bar__brand" href="#/">
        <span className="nav-bar__eyebrow">SLC</span>
      </a>

      <nav className="nav-bar__links" aria-label="Site sections">
        {routes.map((route) => {
          const isActive = route.path === currentPath
          return (
            <a
              key={route.path}
              href={`#${route.path}`}
              className={isActive ? 'nav-bar__link nav-bar__link--active' : 'nav-bar__link'}
              aria-current={isActive ? 'page' : undefined}
            >
              {route.label}
            </a>
          )
        })}
      </nav>
    </header>
  )
}
