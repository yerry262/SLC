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

export interface Wallet {
  address: string
  alias: string
  balanceEth: number | null
}

export interface WalletsSnapshot {
  generatedAt: string
  method: string
  nodeSource: string
  wallets: Wallet[]
  notes: string[]
}

export interface PriceSnapshot {
  generatedAt: string
  source: string
  ethUsd: number
  marketCapsSource: string
  totalCryptoMarketCapUsd: number | null
  btcMarketCapUsd: number | null
  ethMarketCapUsd: number | null
}

export interface BlockProposal {
  slot: number
  validatorIndex: number
  validatorPubkey: string | null
  blockNumber: number | null
  priorityFeeRevenueEth: number | null
  builderPaymentNote: string | null
  revenueError: string | null
}

export interface BlocksSnapshot {
  generatedAt: string
  method: string
  depositAddress: string
  scanProgress: {
    headSlot: number
    oldestValidatorActivationSlot: number
    scannedRanges: [number, number][]
    slotsScannedTotal: number
    fullHistoryComplete: boolean
  }
  proposals: BlockProposal[]
  totalConfirmedProposals: number
  totalPriorityFeeRevenueEth: number
  notes: string[]
}

export interface RewardsValidator {
  index: number
  pubkey: string
  status: string
  daysSinceActivation: number | null
  clRewardEth: number | null
  roiPct: number | null
  annualizedPct: number | null
  unavailableReason: string | null
}

export interface RewardsFleetSummary {
  validatorsTracked: number
  validatorsTotal: number
  totalClRewardEth: number
  avgRoiPct: number | null
  avgAnnualizedPct: number | null
}

export interface RewardsSnapshot {
  generatedAt: string
  method: string
  sourceFleetGeneratedAt: string
  baseStakeEth: number
  fleetSummary: RewardsFleetSummary
  validators: RewardsValidator[]
  notes: string[]
}
