import { SlotStrip } from './components/SlotStrip'
import { FleetSummary } from './components/FleetSummary'
import { ValidatorTable } from './components/ValidatorTable'
import { mockFleet } from './data/mockFleet'
import './App.css'

function App() {
  const { currentEpoch, slots, validators } = mockFleet

  return (
    <div className="app">
      <header className="app__header">
        <span className="app__eyebrow">SLC</span>
        <h1 className="app__title">Validator Watch</h1>
      </header>

      <SlotStrip epoch={currentEpoch} slots={slots} />

      <div className="app__body">
        <FleetSummary validators={validators} />
        <ValidatorTable validators={validators} />
      </div>
    </div>
  )
}

export default App
