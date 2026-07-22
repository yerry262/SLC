export type ValidatorStatus = 'active' | 'exited' | 'slashed' | 'pending'

export interface Validator {
  index: number
  pubkey: string
  status: ValidatorStatus
  balanceEth: number
  activationEpoch: number
  daysOnline: number | null
}

export interface EpochSlot {
  slot: number
  proposedByUs: boolean
  missed: boolean
}

export interface FleetSnapshot {
  generatedAt: string
  discoverySource: string
  depositAddress: string
  currentEpoch: number
  validators: Validator[]
}

export interface EarningsValidator {
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

export interface EarningsSnapshot {
  generatedAt: string
  method: string
  depositAddress: string
  feeRecipientConfigSource: string
  defaultFeeRecipient: string
  scanWindow: {
    headSlot: number
    fromSlot: number
    toSlot: number
    slotsScanned: number
    daysScanned: number
  }
  validators: EarningsValidator[]
  notes: string[]
}
