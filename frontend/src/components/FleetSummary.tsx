import type { Validator } from '../types'
import './FleetSummary.css'

interface FleetSummaryProps {
  validators: Validator[]
}

export function FleetSummary({ validators }: FleetSummaryProps) {
  const active = validators.filter((v) => v.status === 'active')
  const totalBalance = validators.reduce((sum, v) => sum + v.balanceEth, 0)
  const avgDaysOnline =
    active.length > 0 ? Math.round(active.reduce((sum, v) => sum + v.daysOnline, 0) / active.length) : 0

  return (
    <div className="fleet-summary">
      <h2 className="fleet-summary__title">Fleet</h2>

      <dl className="fleet-summary__stat">
        <dt>active validators</dt>
        <dd>{active.length}</dd>
      </dl>

      <dl className="fleet-summary__stat">
        <dt>total balance</dt>
        <dd>
          {totalBalance.toFixed(4)} <span className="fleet-summary__unit">ETH</span>
        </dd>
      </dl>

      <dl className="fleet-summary__stat">
        <dt>avg. days online</dt>
        <dd>{avgDaysOnline}</dd>
      </dl>
    </div>
  )
}
