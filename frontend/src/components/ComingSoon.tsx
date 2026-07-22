import './ComingSoon.css'

interface ComingSoonProps {
  /** Section title, matches the nav label (e.g. "Our Rewards"). */
  title: string
  /** Honest, specific explanation of the gap — no placeholder/lorem copy. */
  description: string
}

/**
 * Shared empty state for nav routes that exist but aren't wired up yet.
 * Deliberately not a blank page or a 404 — same "notice" convention as
 * EarningsPanel's/PerformancePanel's caveat boxes, generalized so any
 * future route can use it until it has a real page component.
 */
export function ComingSoon({ title, description }: ComingSoonProps) {
  return (
    <div className="coming-soon-page">
      <section className="coming-soon">
        <header className="coming-soon__header">
          <h2 className="coming-soon__title">{title}</h2>
        </header>

        <div className="coming-soon__notice">
          <span className="coming-soon__notice-label">not wired up yet</span>
          <p>{description}</p>
        </div>
      </section>
    </div>
  )
}
