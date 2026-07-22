import type { Validator, EarningsSnapshot } from '../types'
import './FleetSummary.css'

interface FleetSummaryProps {
  validators: Validator[]
  earnings: EarningsSnapshot
}

const STAKE_PER_VALIDATOR = 32

export function FleetSummary({ validators, earnings }: FleetSummaryProps) {
  const active = validators.filter((v) => v.status === 'active')
  const totalBalance = validators.reduce((sum, v) => sum + v.balanceEth, 0)
  const baseStake = active.length * STAKE_PER_VALIDATOR
  const consensusRewards = active.reduce((sum, v) => sum + Math.max(0, v.balanceEth - STAKE_PER_VALIDATOR), 0)
  const tipsInWindow = earnings.validators.reduce((sum, v) => sum + v.confirmedTipsEthInScanWindow, 0)
  const knownDaysOnline = active.map((v) => v.daysOnline).filter((d): d is number => d !== null)
  const avgDaysOnline =
    knownDaysOnline.length > 0 ? Math.round(knownDaysOnline.reduce((sum, d) => sum + d, 0) / knownDaysOnline.length) : 0

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

      <div className="fleet-summary__breakdown">
        <div className="fleet-summary__breakdown-row">
          <span className="fleet-summary__breakdown-label">base stake</span>
          <span className="fleet-summary__breakdown-value">{baseStake.toFixed(4)} ETH</span>
        </div>
        <div className="fleet-summary__breakdown-row">
          <span className="fleet-summary__breakdown-label">consensus rewards</span>
          <span className="fleet-summary__breakdown-value fleet-summary__breakdown-value--cyan">
            +{consensusRewards.toFixed(4)} ETH
          </span>
        </div>
        <div className="fleet-summary__breakdown-row">
          <span className="fleet-summary__breakdown-label">
            tips <span className="fleet-summary__breakdown-window">({earnings.scanWindow.daysScanned.toFixed(1)}d window)</span>
          </span>
          <span className="fleet-summary__breakdown-value fleet-summary__breakdown-value--cyan">
            +{tipsInWindow.toFixed(4)} ETH
          </span>
        </div>
      </div>

      <dl className="fleet-summary__stat">
        <dt>avg. days online</dt>
        <dd>{avgDaysOnline}</dd>
      </dl>
    </div>
  )
}
