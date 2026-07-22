import rewardsData from '../data/rewards.json'
import priceData from '../data/price.json'
import type { PriceSnapshot, RewardsSnapshot, RewardsValidator } from '../types'
import './RewardsPage.css'

const rewards = rewardsData as RewardsSnapshot
const price = priceData as PriceSnapshot

function truncateHex(value: string) {
  return value.length > 16 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value
}

function formatUsd(usd: number) {
  return usd.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
}

function formatGeneratedAt(iso: string) {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      })
}

function isTracked(v: RewardsValidator): v is RewardsValidator & { roiPct: number; annualizedPct: number | null; clRewardEth: number; daysSinceActivation: number } {
  return v.roiPct !== null
}

/**
 * Standalone `/rewards` page — closes MIGRATE.md's "APR / ROI% metrics and
 * CL-reward figures" gap (Validator_Earnings.ipynb / Validator_Staking_Calc.ipynb).
 * See scripts/fetch_rewards.py's docstring for the full methodology this
 * page just renders: ROI% and an annualized rate are computed from
 * fleet.json's balanceEth/activationEpoch, NOT from beaconcha.in (confirmed
 * dead) and NOT a true trailing 7d/31d/365d APR — see the notice below and
 * the methodology details at the bottom of the page before trusting any
 * number here as more precise than it is.
 */
export function RewardsPage() {
  const { fleetSummary, validators, notes } = rewards
  const untrackedCount = fleetSummary.validatorsTotal - fleetSummary.validatorsTracked

  return (
    <div className="rewards-page">
      <header className="rewards-page__header">
        <span className="rewards-page__eyebrow">SLC · Rewards</span>
        <h1 className="rewards-page__title">Our Rewards</h1>
      </header>

      <div className="rewards-page__notice">
        <span className="rewards-page__notice-label">since-activation average, not a trailing APR</span>
        <p>
          Every rate below is a <strong>whole-life average since each validator activated</strong>,
          extrapolated to an annual figure — not a true trailing 7d/31d/365d APR like the old
          beaconcha.in-scraped dashboard showed. beaconcha.in itself is confirmed dead (its HTML page
          403s, its API key is zero-quota) so nothing here comes from it. A real trailing-window figure
          would need historical balance snapshots this repo doesn&apos;t keep yet — fleet.json is a
          single point-in-time snapshot, overwritten on every run. See &ldquo;methodology &amp;
          caveats&rdquo; below for the full explanation.
        </p>
      </div>

      <section className="rewards-page__stats">
        <dl className="rewards-page__stat">
          <dt>total CL reward, tracked validators</dt>
          <dd className="rewards-page__stat--cyan">
            {fleetSummary.totalClRewardEth.toFixed(4)} <span className="rewards-page__unit">ETH</span>
          </dd>
          {price && (
            <span
              className="rewards-page__stat-usd"
              title={`1 ETH ≈ ${formatUsd(price.ethUsd)} (${price.source})`}
            >
              ≈ {formatUsd(fleetSummary.totalClRewardEth * price.ethUsd)}
            </span>
          )}
          <span className="rewards-page__stat-sub">above the 32 ETH base stake, since activation</span>
        </dl>

        <dl className="rewards-page__stat">
          <dt>avg ROI% since activation</dt>
          <dd>{fleetSummary.avgRoiPct === null ? '—' : `${fleetSummary.avgRoiPct.toFixed(2)}%`}</dd>
          <span className="rewards-page__stat-sub">simple mean across tracked validators</span>
        </dl>

        <dl className="rewards-page__stat">
          <dt>avg annualized rate</dt>
          <dd>{fleetSummary.avgAnnualizedPct === null ? '—' : `${fleetSummary.avgAnnualizedPct.toFixed(2)}%`}</dd>
          <span className="rewards-page__stat-sub">whole-life average, extrapolated — not trailing APR</span>
        </dl>

        <dl className="rewards-page__stat">
          <dt>validators tracked</dt>
          <dd>
            {fleetSummary.validatorsTracked} <span className="rewards-page__unit">/ {fleetSummary.validatorsTotal}</span>
          </dd>
          <span className="rewards-page__stat-sub">
            {untrackedCount > 0 ? `${untrackedCount} exited/pending, excluded — see table` : 'all validators active'}
          </span>
        </dl>
      </section>

      <div className="rewards-page__table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col" className="rewards-page__status-col">
                status
              </th>
              <th scope="col">pubkey</th>
              <th scope="col">days since activation</th>
              <th scope="col">CL reward</th>
              <th scope="col">ROI% since activation</th>
              <th scope="col">annualized rate</th>
            </tr>
          </thead>
          <tbody>
            {validators.map((v) => (
              <tr key={v.index}>
                <td>
                  <span className={`rewards-page__dot rewards-page__dot--${v.status}`} title={v.status} />
                </td>
                <td className="rewards-page__mono" title={v.pubkey}>
                  {truncateHex(v.pubkey)}
                </td>
                <td className="rewards-page__mono">
                  {v.daysSinceActivation === null ? '—' : v.daysSinceActivation.toFixed(0)}
                </td>
                {isTracked(v) ? (
                  <>
                    <td className="rewards-page__mono">{v.clRewardEth.toFixed(4)} ETH</td>
                    <td className="rewards-page__mono">{v.roiPct.toFixed(2)}%</td>
                    <td className="rewards-page__mono">
                      {v.annualizedPct === null ? 'n/a' : `${v.annualizedPct.toFixed(2)}%`}
                    </td>
                  </>
                ) : (
                  <>
                    <td className="rewards-page__mono rewards-page__cell--unavailable" title={v.unavailableReason ?? undefined}>
                      n/a
                    </td>
                    <td className="rewards-page__mono rewards-page__cell--unavailable" title={v.unavailableReason ?? undefined}>
                      n/a
                    </td>
                    <td className="rewards-page__mono rewards-page__cell--unavailable" title={v.unavailableReason ?? undefined}>
                      n/a
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className="rewards-page__footer">
        <span className="rewards-page__generated">
          generated {formatGeneratedAt(rewards.generatedAt)} · derived from fleet snapshot{' '}
          {formatGeneratedAt(rewards.sourceFleetGeneratedAt)}
        </span>
        <details className="rewards-page__notes">
          <summary>methodology &amp; caveats ({notes.length})</summary>
          <ul>
            {notes.map((note) => (
              <li key={note.slice(0, 40)}>{note}</li>
            ))}
          </ul>
        </details>
      </footer>
    </div>
  )
}
