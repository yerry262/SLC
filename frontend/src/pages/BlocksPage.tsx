import blocksData from '../data/blocks.json'
import type { BlockProposal, BlocksSnapshot } from '../types'
import './BlocksPage.css'

const blocks = blocksData as BlocksSnapshot

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

function proposalKey(p: BlockProposal) {
  return `${p.slot}-${p.validatorIndex}`
}

/**
 * Standalone `/blocks` page — every block our validators have ever actually
 * PROPOSED (Validator_Staking_Blocks.ipynb's core content), discovered by a
 * resumable header-walk (scripts/fetch_blocks.py) that works at any
 * historical depth. MISSED slots specifically attributable to one of our
 * validators are a separate, forward-only near-head signal (see
 * scanProgress notes and the coverage caveat below) — this page is honest
 * about that gap rather than fabricating a lifetime miss count.
 */
export function BlocksPage() {
  const { scanProgress, proposals, totalConfirmedProposals, totalPriorityFeeRevenueEth, notes } = blocks
  const coveragePct = Math.min(
    100,
    (scanProgress.slotsScannedTotal / (scanProgress.headSlot - scanProgress.oldestValidatorActivationSlot + 1)) * 100,
  )

  return (
    <div className="blocks-page">
      <header className="blocks-page__header">
        <span className="blocks-page__eyebrow">SLC</span>
        <h1 className="blocks-page__title">Our Blocks</h1>
      </header>

      <section className="blocks-page__summary">
        <dl className="blocks-page__stat">
          <dt>confirmed proposals tracked</dt>
          <dd>{totalConfirmedProposals}</dd>
          <span className="blocks-page__stat-sub">since scanning began, not a full lifetime count yet</span>
        </dl>

        <dl className="blocks-page__stat">
          <dt>priority-fee revenue, tracked proposals</dt>
          <dd className="blocks-page__stat--cyan">
            {totalPriorityFeeRevenueEth.toFixed(6)} <span className="blocks-page__unit">ETH</span>
          </dd>
          <span className="blocks-page__stat-sub">measured from tracked blocks only</span>
        </dl>

        <div className="blocks-page__coverage">
          <div className="blocks-page__coverage-row">
            <span className="blocks-page__coverage-label">history scan coverage</span>
            <span className="blocks-page__coverage-value">{coveragePct.toFixed(2)}%</span>
          </div>
          <div className="blocks-page__progress-track">
            <div className="blocks-page__progress-fill" style={{ width: `${coveragePct}%` }} />
          </div>
          <span className="blocks-page__coverage-sub">
            {scanProgress.slotsScannedTotal.toLocaleString()} slots scanned toward slot{' '}
            {scanProgress.oldestValidatorActivationSlot.toLocaleString()} (our oldest validator's activation)
            {scanProgress.fullHistoryComplete ? ' — complete' : ' — in progress, re-run to extend'}
          </span>
        </div>
      </section>

      <div className="blocks-page__notice">
        <span className="blocks-page__notice-label">missed slots not shown here</span>
        <p>
          This page tracks confirmed PROPOSALS only. Attributing a missed slot to one of our validators
          specifically needs the proposer-duty schedule, which this node can only compute cheaply for a
          near-head window (roughly the last 5-9 epochs) — older epochs can't be attributed to a specific
          validator, so historical misses aren't reported rather than guessed. Forward-tracked near-head
          misses (real, but only since tracking began) are counted in the Performance panel on the
          Dashboard instead.
        </p>
      </div>

      <div className="blocks-page__table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">slot</th>
              <th scope="col">validator</th>
              <th scope="col">block</th>
              <th scope="col">priority-fee revenue</th>
              <th scope="col">note</th>
            </tr>
          </thead>
          <tbody>
            {proposals.length === 0 && (
              <tr>
                <td colSpan={5} className="blocks-page__empty">
                  No confirmed proposals in the range scanned so far — expected: with 13 of over 1,000,000
                  active mainnet validators, this fleet proposes roughly once every 1-2 months.
                </td>
              </tr>
            )}
            {proposals.map((p) => (
              <tr key={proposalKey(p)}>
                <td className="blocks-page__mono">{p.slot.toLocaleString()}</td>
                <td className="blocks-page__mono" title={p.validatorPubkey ?? undefined}>
                  #{p.validatorIndex}
                  {p.validatorPubkey ? ` · ${truncateHex(p.validatorPubkey)}` : ''}
                </td>
                <td className="blocks-page__mono">
                  {p.blockNumber ? (
                    <a
                      href={`https://etherscan.io/block/${p.blockNumber}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {p.blockNumber.toLocaleString()}
                    </a>
                  ) : (
                    'n/a'
                  )}
                </td>
                <td className="blocks-page__mono">
                  {p.revenueError
                    ? 'error'
                    : p.priorityFeeRevenueEth !== null
                      ? `${p.priorityFeeRevenueEth.toFixed(6)} ETH`
                      : 'n/a'}
                </td>
                <td className="blocks-page__cell--dim">{p.builderPaymentNote ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className="blocks-page__footer">
        <span className="blocks-page__generated">generated {formatGeneratedAt(blocks.generatedAt)}</span>
        <details className="blocks-page__notes">
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
