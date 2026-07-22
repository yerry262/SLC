import './SiteFooter.css'

// Version string ported from SLC-DASHBOARD-2024/SLC/version.py
// (`ver='SLC v0.3,0'` — read as v0.3.0; the comma looks like a source typo
// for a period). This is just the display string, not a version-bumping
// scheme — bump it by hand when it's worth it. version.py's `easteregg` flag
// coupled the old dashboard to hidden visitor-analytics tracking and is
// deliberately NOT ported; see MIGRATE.md's "Read this first" hazards
// section and the `version.py` row in its file-by-file map.
const APP_VERSION = 'SLC v0.3.0'

// Disclaimer ported in spirit (not verbatim) from
// SLC-DASHBOARD-2024/SLC/Funct.py's BOTTOM_WARNING constant — see MIGRATE.md's
// Funct.py row ("worth carrying over in spirit if this ever shows real
// financial figures to anyone but yerry"), now true: Dashboard shows a USD
// balance estimate (FleetSummary) and Wallets shows real balances
// (WalletsPage). This is the small, sitewide version and deliberately
// shorter than MissionPage.tsx's own bespoke disclaimer paragraph — that one
// stays as-is; this one just needs to show up everywhere else too.
export function SiteFooter() {
  return (
    <footer className="site-footer">
      <span className="site-footer__version">{APP_VERSION}</span>
      <p className="site-footer__disclaimer">
        <strong>Disclaimer:</strong> Balances, tips, and USD estimates shown on this site are
        informational only and may be incomplete, delayed, or approximate — not financial, investment,
        tax, legal, or accounting advice. Consult a qualified professional before making decisions based
        on these figures.
      </p>
    </footer>
  )
}
