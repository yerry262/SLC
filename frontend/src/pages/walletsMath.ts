export const VALIDATOR_STAKE_ETH = 32

export interface NextValidatorCountdown {
  fundableNow: number
  remainderEth: number
  neededEth: number
}

/**
 * Ports Validator_Wallets.ipynb's "how much ETH until the next 32-ETH
 * validator" figure — but as a pure function of the total balance, not a
 * stored value. Called fresh on every WalletsPage render from
 * wallets.json's balances, so it can never go stale relative to the
 * balance it's derived from (see scripts/fetch_wallets.py's notes and this
 * repo's MIGRATE.md, Stage 6). Kept in its own module (rather than
 * WalletsPage.tsx) so it's independently importable/testable and doesn't
 * trip react-refresh's only-export-components rule.
 */
export function computeNextValidatorCountdown(
  totalBalanceEth: number,
  thresholdEth: number = VALIDATOR_STAKE_ETH,
): NextValidatorCountdown {
  if (!Number.isFinite(totalBalanceEth) || totalBalanceEth <= 0 || thresholdEth <= 0) {
    return { fundableNow: 0, remainderEth: 0, neededEth: Math.max(0, thresholdEth) }
  }
  const fundableNow = Math.floor(totalBalanceEth / thresholdEth)
  const remainderEth = totalBalanceEth - fundableNow * thresholdEth
  const neededEth = thresholdEth - remainderEth
  return { fundableNow, remainderEth, neededEth }
}
