import walletsData from '../data/wallets.json'
import type { Wallet, WalletsSnapshot } from '../types'
import { computeNextValidatorCountdown, VALIDATOR_STAKE_ETH } from './walletsMath'
import './WalletsPage.css'

const wallets = walletsData as WalletsSnapshot

function truncateHex(value: string) {
  return value.length > 16 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value
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

function isKnownBalance(w: Wallet): w is Wallet & { balanceEth: number } {
  return w.balanceEth !== null
}

/**
 * Standalone `/wallets` page — the "Wallet Information (Liquid)" section of
 * the old Validator_Wallets.ipynb notebook (the "Validator Information
 * (illiquid)" section is superseded by fleet.json/FleetSummary and isn't
 * repeated here). Self-contained (own header/layout) so it can be dropped
 * into a router as its own route without depending on App.tsx.
 *
 * The "validator" column is a real cross-reference against earnings.json's
 * feeRecipient data (fetch_wallets.py), not the old Varibles.py's generic
 * "Validator N Tip Jar" ordinal labels — those predate our newest
 * validator and have no link to real validator indices. A wallet can map
 * to more than one index (shared default fee_recipient) or none (Weekly
 * Base Pay, Deployer aren't fee recipients at all).
 */
export function WalletsPage() {
  const { wallets: walletList, notes } = wallets
  const knownWallets = walletList.filter(isKnownBalance)
  const unavailableCount = walletList.length - knownWallets.length
  const totalBalanceEth = knownWallets.reduce((sum, w) => sum + w.balanceEth, 0)
  const countdown = computeNextValidatorCountdown(totalBalanceEth)
  const progressPct = Math.min(100, (countdown.remainderEth / VALIDATOR_STAKE_ETH) * 100)

  return (
    <div className="wallets-page">
      <header className="wallets-page__header">
        <span className="wallets-page__eyebrow">SLC</span>
        <h1 className="wallets-page__title">Wallets</h1>
      </header>

      <section className="wallets-page__summary">
        <dl className="wallets-page__stat">
          <dt>total liquid balance</dt>
          <dd>
            {totalBalanceEth.toFixed(4)} <span className="wallets-page__unit">ETH</span>
          </dd>
          <span className="wallets-page__stat-sub">
            across {knownWallets.length} of {walletList.length} wallets
            {unavailableCount > 0 ? `, ${unavailableCount} unavailable` : ''}
          </span>
        </dl>

        <div className="wallets-page__countdown">
          <div className="wallets-page__countdown-row">
            <span className="wallets-page__countdown-label">eth until next validator</span>
            <span className="wallets-page__countdown-value">{countdown.neededEth.toFixed(4)} ETH</span>
          </div>
          <div className="wallets-page__progress-track">
            <div className="wallets-page__progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <span className="wallets-page__countdown-sub">
            {countdown.remainderEth.toFixed(4)} / {VALIDATOR_STAKE_ETH} ETH toward the next 32-ETH validator
            {countdown.fundableNow > 0 ? ` — ${countdown.fundableNow} more already fundable now` : ''}
          </span>
        </div>
      </section>

      {unavailableCount > 0 && (
        <div className="wallets-page__notice">
          <span className="wallets-page__notice-label">some balances unavailable</span>
          <p>
            eth_getBalance failed for {unavailableCount} wallet{unavailableCount === 1 ? '' : 's'} on the last
            fetch — left blank rather than shown as zero. The total and countdown above only include wallets
            with a confirmed balance.
          </p>
        </div>
      )}

      <div className="wallets-page__table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">wallet</th>
              <th scope="col">alias</th>
              <th scope="col">validator</th>
              <th scope="col">balance</th>
            </tr>
          </thead>
          <tbody>
            {walletList.map((w) => (
              <tr key={w.address}>
                <td className="wallets-page__mono">
                  <a href={`https://etherscan.io/address/${w.address}`} target="_blank" rel="noreferrer" title={w.address}>
                    {truncateHex(w.address)}
                  </a>
                </td>
                <td>{w.alias}</td>
                <td className="wallets-page__mono">
                  {w.validatorIndices.length === 0 ? (
                    <span className="wallets-page__cell--unavailable">—</span>
                  ) : (
                    w.validatorIndices.map((idx) => `#${idx}`).join(', ')
                  )}
                </td>
                <td className={w.balanceEth === null ? 'wallets-page__mono wallets-page__cell--unavailable' : 'wallets-page__mono'}>
                  {w.balanceEth === null ? 'n/a' : `${w.balanceEth.toFixed(4)} ETH`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className="wallets-page__footer">
        <span className="wallets-page__generated">generated {formatGeneratedAt(wallets.generatedAt)}</span>
        <details className="wallets-page__notes">
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
