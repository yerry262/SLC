import type { ReactElement } from 'react'
import { Dashboard } from '../pages/Dashboard'
import { MissionPage } from '../pages/MissionPage'
import { RewardsPage } from '../pages/RewardsPage'
import { WalletsPage } from '../pages/WalletsPage'
import { BlocksPage } from '../pages/BlocksPage'
import { ComingSoon } from '../components/ComingSoon'

export interface RouteConfig {
  path: string
  label: string
  element: ReactElement
}

// Labels match Main_Menu.ipynb's `button_notebooks` dict exactly (minus
// "Online Status", folded into Dashboard per MIGRATE.md's target-structure
// decision — fleet.json's `status` + PerformancePanel's dot already cover
// it there). "Dashboard" is new: the old notebook had no named button for
// it, it was just whatever loaded first.
//
// Each non-dashboard entry below is a placeholder today. Swapping one in
// for a real page is a one-line change to its `element` — see MIGRATE.md's
// per-route stage notes for what each is actually waiting on.
export const routes: RouteConfig[] = [
  {
    path: '/',
    label: 'Dashboard',
    element: <Dashboard />,
  },
  {
    path: '/mission',
    label: 'Our Mission',
    element: <MissionPage />,
  },
  {
    path: '/rewards',
    label: 'Our Rewards',
    element: <RewardsPage />,
  },
  {
    path: '/blocks',
    label: 'Our Blocks',
    element: <BlocksPage />,
  },
  {
    path: '/staking-calculator',
    label: 'Staking Calculator',
    element: (
      <ComingSoon
        title="Staking Calculator"
        description="Despite the name, the old notebook this replaces isn't a projection calculator — it's the same rewards data as Our Rewards, filtered per validator and summed. It depends on the same reward data that isn't wired up yet."
      />
    ),
  },
  {
    path: '/investor-calculator',
    label: 'Investor Calculator',
    element: (
      <ComingSoon
        title="Investor Calculator"
        description="Real per-investor dollar figures and wallet-to-person mapping are gated on an explicit go/no-go decision — this is sensitive per-person financial data, not validator performance data. This page intentionally shows no real figures until that decision is made."
      />
    ),
  },
  {
    path: '/wallets',
    label: 'Wallets',
    element: <WalletsPage />,
  },
]

export const defaultRoute = routes[0]
