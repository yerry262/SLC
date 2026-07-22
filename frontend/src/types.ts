export type ValidatorStatus = 'active' | 'exited' | 'slashed' | 'pending'

export interface Validator {
  index: number
  pubkey: string
  status: ValidatorStatus
  balanceEth: number
  activationEpoch: number
  daysOnline: number
}

export interface EpochSlot {
  slot: number
  proposedByUs: boolean
  missed: boolean
}

export interface FleetSnapshot {
  currentEpoch: number
  slots: EpochSlot[]
  validators: Validator[]
}
