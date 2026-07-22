import type { EpochSlot } from '../types'
import './SlotStrip.css'

interface SlotStripProps {
  epoch: number
  slots: EpochSlot[]
}

export function SlotStrip({ epoch, slots }: SlotStripProps) {
  return (
    <div className="slot-strip">
      <div className="slot-strip__label">
        <span className="slot-strip__eyebrow">EPOCH</span>
        <span className="slot-strip__epoch">{epoch}</span>
      </div>
      <div className="slot-strip__ticks" role="img" aria-label={`32 slots in epoch ${epoch}, ticks lit where our validators proposed`}>
        {slots.map((s) => (
          <span
            key={s.slot}
            className={
              'slot-strip__tick' +
              (s.proposedByUs ? ' slot-strip__tick--proposed' : '') +
              (s.missed ? ' slot-strip__tick--missed' : '')
            }
            title={`slot ${s.slot}${s.proposedByUs ? ' — proposed by us' : ''}${s.missed ? ' — missed' : ''}`}
          />
        ))}
      </div>
    </div>
  )
}
