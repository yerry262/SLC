import type { FleetSnapshot } from '../types'

// Placeholder data for the Stage 1 layout pass — replaced in Stage 2 by a
// real snapshot generated from the local node (see project plan).
export const mockFleet: FleetSnapshot = {
  currentEpoch: 41891,
  slots: Array.from({ length: 32 }, (_, slot) => ({
    slot,
    proposedByUs: [3, 11, 22].includes(slot),
    missed: slot === 17,
  })),
  validators: [
    {
      index: 166200,
      pubkey: '0x820bbe4c8c19d21f0cf32257ced118aa43badb9c768d7854cc91f79b72f3d5472f47eab1b54477eb72fbb3ff10eeaebf',
      status: 'active',
      balanceEth: 32.7205,
      activationEpoch: 44062,
      daysOnline: 1878,
    },
    {
      index: 166201,
      pubkey: '0x8007ad5fb5308d01886cf4fed6b7878a423e4f5619889e193f0e2ff0f70d4ba549553cfa76ed6702cb50dd50cb3d8570',
      status: 'active',
      balanceEth: 34.1256,
      activationEpoch: 44070,
      daysOnline: 1878,
    },
    {
      index: 166202,
      pubkey: '0x85e97d5a9bf9b934bd83a5b399ebe9e39bbaba6d686119d2f01d1ecf5a038a8932089ba505399d46d0dc62090fd9a101',
      status: 'exited',
      balanceEth: 0,
      activationEpoch: 44075,
      daysOnline: 1200,
    },
  ],
}
