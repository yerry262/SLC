import earningsData from '../data/earnings.json'
import priceData from '../data/price.json'
import type { PriceSnapshot } from '../types'
import './EarningsPanel.css'

interface EarningsScanWindow {
  headSlot: number
  fromSlot: number
  toSlot: number
  slotsScanned: number
  daysScanned: number
}

interface EarningsValidator {
  index: number
  pubkey: string
  status: string
  feeRecipient: string | null
  builderEnabled: boolean
  feeRecipientSource: string
  confirmedProposalCount: number
  confirmedTipsEthInScanWindow: number
  lifetimeProposalCount: number | null
  lifetimeTipsEth: number | null
}

interface EarningsSnapshot {
  generatedAt: string
  method: string
  depositAddress: string
  feeRecipientConfigSource: string
  defaultFeeRecipient: string
  scanWindow: EarningsScanWindow
  validators: EarningsValidator[]
  notes: string[]
}

const earnings = earningsData as EarningsSnapshot
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

export function EarningsPanel() {
  const { scanWindow, validators, notes } = earnings

  const confirmedTipsSum = validators.reduce((sum, v) => sum + v.confirmedTipsEthInScanWindow, 0)
  const confirmedProposalsSum = validators.reduce((sum, v) => sum + v.confirmedProposalCount, 0)
  const lifetimeTracked = validators.some((v) => v.lifetimeTipsEth !== null)

  return (
    <section className="earnings-panel">
      <header className="earnings-panel__header">
        <h2 className="earnings-panel__title">Earnings</h2>
        <span className="earnings-panel__generated" title={earnings.method}>
          scanned {formatGeneratedAt(earnings.generatedAt)}
        </span>
      </header>

      <div className="earnings-panel__stats">
        <dl className="earnings-panel__stat">
          <dt>scan window</dt>
          <dd>
            {scanWindow.daysScanned.toFixed(1)} <span className="earnings-panel__unit">days</span>
          </dd>
          <span className="earnings-panel__stat-sub">
            {scanWindow.slotsScanned.toLocaleString()} slots · #{scanWindow.fromSlot.toLocaleString()}–
            {scanWindow.toSlot.toLocaleString()}
          </span>
        </dl>

        <dl className="earnings-panel__stat">
          <dt>confirmed tips, scan window</dt>
          <dd className="earnings-panel__stat--cyan">
            {confirmedTipsSum.toFixed(4)} <span className="earnings-panel__unit">ETH</span>
          </dd>
          {price && (
            <span className="earnings-panel__stat-usd" title={`1 ETH ≈ ${formatUsd(price.ethUsd)} (${price.source})`}>
              ≈ {formatUsd(confirmedTipsSum * price.ethUsd)}
            </span>
          )}
          <span className="earnings-panel__stat-sub">measured, not lifetime</span>
        </dl>

        <dl className="earnings-panel__stat">
          <dt>confirmed proposals, scan window</dt>
          <dd>{confirmedProposalsSum}</dd>
          <span className="earnings-panel__stat-sub">across {validators.length} validators</span>
        </dl>

        <dl className="earnings-panel__stat">
          <dt>lifetime tips</dt>
          <dd className="earnings-panel__stat--unavailable">not tracked</dd>
          <span className="earnings-panel__stat-sub">see notice below</span>
        </dl>
      </div>

      {!lifetimeTracked && (
        <div className="earnings-panel__notice">
          <span className="earnings-panel__notice-label">tip tracking not yet complete</span>
          <p>
            Every figure above is a real, measured value from this scan window only — not a lifetime
            total. Lifetime proposal and tip history isn&apos;t available yet: it lives in Prysm&apos;s
            slashing-protection database on the node, and exporting it requires briefly stopping the
            live validator service. That hasn&apos;t been done, so lifetime fields are left blank here
            rather than shown as zero.
          </p>
        </div>
      )}

      <div className="earnings-panel__table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col" className="earnings-panel__status-col">
                status
              </th>
              <th scope="col">pubkey</th>
              <th scope="col">fee recipient</th>
              <th scope="col">builder</th>
              <th scope="col">tips, scan window</th>
              <th scope="col">tips, lifetime</th>
            </tr>
          </thead>
          <tbody>
            {validators.map((v) => (
              <tr key={v.index}>
                <td>
                  <span className={`earnings-panel__dot earnings-panel__dot--${v.status}`} title={v.status} />
                </td>
                <td className="earnings-panel__mono" title={v.pubkey}>
                  {truncateHex(v.pubkey)}
                </td>
                <td className="earnings-panel__mono" title={v.feeRecipientSource}>
                  {v.feeRecipient ? truncateHex(v.feeRecipient) : '—'}
                </td>
                <td>{v.builderEnabled ? 'yes' : 'no'}</td>
                <td className="earnings-panel__mono">{v.confirmedTipsEthInScanWindow.toFixed(4)} ETH</td>
                <td className="earnings-panel__mono earnings-panel__cell--unavailable" title="not tracked yet">
                  {v.lifetimeTipsEth === null ? 'n/a' : `${v.lifetimeTipsEth.toFixed(4)} ETH`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="earnings-panel__notes">
        <summary>methodology &amp; caveats ({notes.length})</summary>
        <ul>
          {notes.map((note) => (
            <li key={note.slice(0, 40)}>{note}</li>
          ))}
        </ul>
      </details>
    </section>
  )
}
