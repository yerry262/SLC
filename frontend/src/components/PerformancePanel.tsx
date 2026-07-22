import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { TooltipContentProps } from 'recharts'
import performanceData from '../data/performance.json'
import './PerformancePanel.css'

// Recharts renders these as raw SVG presentation attributes rather than
// through this component's stylesheet, so CSS custom properties (var(--x))
// aren't a reliable way to feed it colors — these are literal mirrors of
// index.css's design tokens, kept in sync by hand. The two series colors are
// NOT the raw --cyan/--amber values: those are too light (OKLCH L ~0.81) for
// a chart mark on a dark surface per the dataviz skill's categorical
// lightness band (0.48-0.67 dark), so these are deepened steps of the same
// two hues, validated with scripts/validate_palette.js (all six checks pass
// against the --panel surface, worst-pair normal-vision ΔE 21.2).
const CHART_TEXT_DIM = '#8a97a3'
const CHART_HAIRLINE = '#2a323a'
const CHART_PARTICIPATION = '#22a3ac' // deepened --cyan
const CHART_REWARD_EFFECTIVENESS = '#b8791f' // deepened --amber

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

interface AttestationChartRow {
  label: string
  pubkey: string
  participation: number
  rewardEffectiveness: number
}

// Portalled into a plain HTML div (not raw SVG), so — unlike the axis/grid/bar
// colors above — this one can and does use the real design-system CSS
// classes/vars, styled in PerformancePanel.css.
function AttestationChartTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="performance-panel__chart-tooltip">
      <div className="performance-panel__chart-tooltip-label">validator {label}</div>
      {payload.map((entry) => (
        <div key={String(entry.dataKey)} className="performance-panel__chart-tooltip-row">
          <span className="performance-panel__chart-tooltip-swatch" style={{ background: entry.color }} />
          <span className="performance-panel__chart-tooltip-value">
            {formatPct(typeof entry.value === 'number' ? entry.value : null)}
          </span>
          <span className="performance-panel__chart-tooltip-name">{String(entry.name)}</span>
        </div>
      ))}
    </div>
  )
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

  // Same filter the table below effectively applies row-by-row: only
  // validators the local validator client actively reports metrics for.
  // Real data already fetched by fetch_performance.py — no fabricated 0%
  // bars for validators the metrics endpoint has nothing to say about.
  const attestationChartData: AttestationChartRow[] = validators
    .filter((v) => v.attestation.participationRatePct !== null && v.attestation.rewardEffectivenessPct !== null)
    .map((v) => ({
      label: `#${v.index}`,
      pubkey: v.pubkey,
      participation: v.attestation.participationRatePct as number,
      rewardEffectiveness: v.attestation.rewardEffectivenessPct as number,
    }))

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

      <div className="performance-panel__chart">
        <div className="performance-panel__chart-heading">
          <h3 className="performance-panel__chart-title">participation vs. reward effectiveness</h3>
          <p className="performance-panel__chart-caption">
            per active validator, current uptime window — exact figures in the table below
          </p>
        </div>
        {attestationChartData.length > 0 ? (
          <div className="performance-panel__chart-plot">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={attestationChartData} barGap={2} barCategoryGap="24%" margin={{ top: 4, right: 8, left: -8, bottom: 4 }}>
                <CartesianGrid stroke={CHART_HAIRLINE} vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: CHART_TEXT_DIM, fontSize: 11, fontFamily: 'var(--font-mono)' }}
                  tickLine={false}
                  axisLine={{ stroke: CHART_HAIRLINE }}
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 25, 50, 75, 100]}
                  tickFormatter={(v: number) => `${v}%`}
                  tick={{ fill: CHART_TEXT_DIM, fontSize: 11, fontFamily: 'var(--font-mono)' }}
                  tickLine={false}
                  axisLine={{ stroke: CHART_HAIRLINE }}
                  width={44}
                />
                <Tooltip
                  content={AttestationChartTooltip}
                  cursor={{ fill: 'rgba(232, 237, 240, 0.05)' }}
                  isAnimationActive={false}
                />
                <Legend
                  verticalAlign="top"
                  align="left"
                  height={28}
                  iconType="rect"
                  iconSize={10}
                  formatter={(value: string) => <span className="performance-panel__chart-legend-label">{value}</span>}
                />
                <Bar
                  dataKey="participation"
                  name="participation rate"
                  fill={CHART_PARTICIPATION}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={18}
                />
                <Bar
                  dataKey="rewardEffectiveness"
                  name="reward effectiveness"
                  fill={CHART_REWARD_EFFECTIVENESS}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={18}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="performance-panel__chart-empty">
            No validators currently report attestation metrics — chart has nothing to plot yet.
          </p>
        )}
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
