import performanceData from '../data/performance.json'
import './PerformancePanel.css'

interface VoteCorrectness {
  head: boolean
  source: boolean
  target: boolean
}

interface BlocksProposed {
  countTracked: number
  recentSlots: number[]
  lifetimeCount: number | null
}

interface AttestationStats {
  lastVoteCorrect: VoteCorrectness | null
  successfulAttestationsSinceProcessStart: number | null
  participationRatePct: number | null
  rewardEffectivenessPct: number | null
  rewardEffectivenessEpochsSampled: number[]
  inactivityScore: number | null
  lastAttestedSlot: number | null
  nextAttestationSlot: number | null
}

interface PerformanceValidator {
  index: number
  pubkey: string
  status: string
  blocksProposed: BlocksProposed
  attestation: AttestationStats
}

interface ProposalScan {
  epochsScannedTotal: number
  epochsScannedThisRun: number[]
  totalConfirmedProposalsTracked: number
}

interface PerformanceSnapshot {
  generatedAt: string
  currentEpoch: number
  currentSlot: number
  validatorClientProcessStartedAt: string
  proposalScan: ProposalScan
  validators: PerformanceValidator[]
  notes: string[]
}

const performance = performanceData as PerformanceSnapshot

function truncateHex(value: string) {
  return value.length > 16 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value
}

function formatDate(iso: string) {
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

function average(values: number[]) {
  return values.length > 0 ? values.reduce((sum, v) => sum + v, 0) / values.length : null
}

function formatPct(value: number | null) {
  return value === null ? '—' : `${value.toFixed(2)}%`
}

export function PerformancePanel() {
  const { validators, proposalScan, notes } = performance

  const activeValidators = validators.filter((v) => v.status === 'active')
  const avgParticipation = average(
    activeValidators.map((v) => v.attestation.participationRatePct).filter((v): v is number => v !== null),
  )
  const avgRewardEffectiveness = average(
    activeValidators.map((v) => v.attestation.rewardEffectivenessPct).filter((v): v is number => v !== null),
  )
  const hasInactiveValidators = validators.some((v) => v.status !== 'active')

  return (
    <section className="performance-panel">
      <header className="performance-panel__header">
        <h2 className="performance-panel__title">Performance</h2>
        <span className="performance-panel__generated" title={`epoch ${performance.currentEpoch} · slot ${performance.currentSlot}`}>
          scanned {formatDate(performance.generatedAt)}
        </span>
      </header>

      <div className="performance-panel__stats">
        <dl className="performance-panel__stat">
          <dt>active validators</dt>
          <dd>{activeValidators.length}</dd>
          <span className="performance-panel__stat-sub">of {validators.length} total</span>
        </dl>

        <dl className="performance-panel__stat">
          <dt>avg. participation rate</dt>
          <dd className="performance-panel__stat--cyan">{formatPct(avgParticipation)}</dd>
          <span className="performance-panel__stat-sub">current uptime window only</span>
        </dl>

        <dl className="performance-panel__stat">
          <dt>avg. reward effectiveness</dt>
          <dd className="performance-panel__stat--cyan">{formatPct(avgRewardEffectiveness)}</dd>
          <span className="performance-panel__stat-sub">
            {activeValidators[0]?.attestation.rewardEffectivenessEpochsSampled.length ?? 0} recent epochs sampled
          </span>
        </dl>

        <dl className="performance-panel__stat">
          <dt>confirmed proposals tracked</dt>
          <dd>{proposalScan.totalConfirmedProposalsTracked}</dd>
          <span className="performance-panel__stat-sub">{proposalScan.epochsScannedTotal} epochs scanned</span>
        </dl>
      </div>

      {hasInactiveValidators && (
        <div className="performance-panel__notice">
          <span className="performance-panel__notice-label">metrics unavailable for exited validators</span>
          <p>
            Attestation and proposal metrics come from the local validator client, which only reports on
            validators it actively manages. Exited validators show as unavailable below rather than zero.
          </p>
        </div>
      )}

      <div className="performance-panel__table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col" className="performance-panel__status-col">
                status
              </th>
              <th scope="col">pubkey</th>
              <th scope="col">participation</th>
              <th scope="col">reward eff.</th>
              <th scope="col">last vote</th>
              <th scope="col">inactivity</th>
              <th scope="col">proposals tracked</th>
              <th scope="col">last attested slot</th>
            </tr>
          </thead>
          <tbody>
            {validators.map((v) => (
              <tr key={v.index}>
                <td>
                  <span className={`performance-panel__dot performance-panel__dot--${v.status}`} title={v.status} />
                </td>
                <td className="performance-panel__mono" title={v.pubkey}>
                  {truncateHex(v.pubkey)}
                </td>
                <td className="performance-panel__mono">{formatPct(v.attestation.participationRatePct)}</td>
                <td className="performance-panel__mono">{formatPct(v.attestation.rewardEffectivenessPct)}</td>
                <td>
                  {v.attestation.lastVoteCorrect ? (
                    <span className="performance-panel__vote-ticks">
                      {(['head', 'source', 'target'] as const).map((k) => (
                        <span
                          key={k}
                          className={
                            'performance-panel__vote-tick' +
                            (v.attestation.lastVoteCorrect?.[k]
                              ? ' performance-panel__vote-tick--correct'
                              : ' performance-panel__vote-tick--incorrect')
                          }
                          title={`${k}: ${v.attestation.lastVoteCorrect?.[k] ? 'correct' : 'incorrect'}`}
                        >
                          {k[0].toUpperCase()}
                        </span>
                      ))}
                    </span>
                  ) : (
                    <span className="performance-panel__cell--unavailable">—</span>
                  )}
                </td>
                <td className="performance-panel__mono">
                  {v.attestation.inactivityScore === null ? '—' : v.attestation.inactivityScore}
                </td>
                <td className="performance-panel__mono">{v.blocksProposed.countTracked}</td>
                <td className="performance-panel__mono">
                  {v.attestation.lastAttestedSlot === null ? '—' : v.attestation.lastAttestedSlot.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="performance-panel__notes">
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
