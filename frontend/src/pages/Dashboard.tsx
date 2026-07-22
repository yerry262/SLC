import { SlotStrip } from '../components/SlotStrip'
import { FleetSummary } from '../components/FleetSummary'
import { ValidatorTable } from '../components/ValidatorTable'
import { PerformancePanel } from '../components/PerformancePanel'
import { EarningsPanel } from '../components/EarningsPanel'
import fleetData from '../data/fleet.json'
import earningsData from '../data/earnings.json'
import type { FleetSnapshot, EarningsSnapshot } from '../types'
import '../App.css'

const fleet = fleetData as FleetSnapshot
const earnings = earningsData as EarningsSnapshot

// Proposal/attestation-per-slot history isn't tracked yet (see
// PerformancePanel's own notes) — render a neutral, unlit strip rather
// than fabricating tick data. The epoch number itself is real.
const neutralSlots = Array.from({ length: 32 }, (_, slot) => ({
  slot,
  proposedByUs: false,
  missed: false,
}))

// Relocated from App.tsx unchanged (Stage 5 nav shell) — this is the "/"
// route now that the top-level shell owns routing/nav instead of the page
// content. Content and component internals untouched.
export function Dashboard() {
  return (
    <div className="app">
      <header className="app__header">
        <span className="app__eyebrow">SLC</span>
        <h1 className="app__title">Validator Watch</h1>
      </header>

      <SlotStrip epoch={fleet.currentEpoch} slots={neutralSlots} />

      <div className="app__body">
        <FleetSummary validators={fleet.validators} earnings={earnings} />
        <ValidatorTable validators={fleet.validators} />
      </div>

      <PerformancePanel />
      <EarningsPanel />
    </div>
  )
}
