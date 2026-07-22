#!/usr/bin/env python3
"""Generate frontend/src/data/rewards.json — ROI% and an annualized
"since-activation" reward rate per validator, computed purely from
frontend/src/data/fleet.json's already-fetched balanceEth/activationEpoch
fields. Closes the MIGRATE.md gap: "APR / ROI% metrics and CL-reward
figures" (Validator_Earnings.ipynb / Validator_Staking_Calc.ipynb).

Method
------
The old notebooks scraped beaconcha.in's HTML validator page for APR
7d/31d/365d and ROI%. That source is confirmed dead (see
scripts/fetch_earnings.py's docstring: the HTML page 403s as bot-protected,
the JSON API key is zero-quota) — no beaconcha.in call happens anywhere in
this script either.

Instead, this derives the same *kind* of figure from data this repo
already has, honestly re-scoped:

  1. Consensus-layer (CL) reward earned since activation, per validator:
       clRewardEth = balanceEth - 32.0
     fleet.json's balanceEth is the validator's current total balance. EL
     tips (priority fees / MEV) are paid to each validator's fee-recipient
     wallet address, NOT credited to the validator's own beacon-chain
     balance (see fetch_earnings.py) — so this delta is CL reward only,
     cleanly separate from earnings.json's EL-tip figures.

  2. Time since activation, from activationEpoch, using the SAME genesis/
     epoch-length constants scripts/fetch_fleet.py uses for its own
     daysOnline field (GENESIS_TS, SECONDS_PER_EPOCH). Duplicated here
     rather than imported — matches this repo's existing convention of
     each fetch_*.py script carrying its own copy of shared constants
     (e.g. NODE_IP/GETH_RPC duplicated across fetch_fleet.py and
     fetch_earnings.py rather than factored into a shared module).

  3. roiPct = clRewardEth / 32.0 * 100 — total return since activation.

  4. annualizedPct = (clRewardEth / 32.0) / daysSinceActivation * 365.25 * 100
     — the whole-life AVERAGE annualized rate, extrapolated out to a year.

Honest limitation — read before trusting this for anything "recent":
this is a since-activation AVERAGE, not a true trailing 7d/31d/365d APR.
It will not reflect a recent change in performance (a bad week of missed
attestations, a client upgrade, etc.) any faster than the validator's
entire multi-year history allows it to move. A real trailing-window figure
needs historical balance snapshots (the balance as of "now minus 7 days",
"now minus 31 days", etc.) that this repo does not keep — fleet.json is a
single point-in-time snapshot, overwritten on every run, with no history
retained anywhere. Building real trailing windows is future work
(MIGRATE.md Stage 7), not something approximated or faked here. See the
"notes" array in the output for the full, explicit caveat list.

Validators that are not (and have not always been) "active" don't get a
figure computed at all, rather than a wrong one:
  - status != "active": an exited validator's balance drops to (or toward)
    0 upon withdrawal, so "balanceEth - 32" at that point measures "already
    withdrew", not lifetime reward. clRewardEth/roiPct/annualizedPct are
    left null, never a fabricated large-negative number.
  - activationEpoch >= PENDING_EPOCH_SENTINEL: not yet activated, so there
    is no "since activation" window yet.

Run: python3 scripts/fetch_rewards.py
Env: none. Unlike every other scripts/fetch_*.py in this repo, this script
makes NO network call at all — it only reads the already-committed
frontend/src/data/fleet.json and does pure arithmetic. In normal operation
it should be run right after scripts/fetch_fleet.py (same CI step or the
next one) so the balances it reads are current — it is a derived view of
fleet.json's data, not an independent fetch, and is not a substitute for
running fetch_fleet.py itself.
"""
import json
import os
import sys
from datetime import datetime, timezone

GENESIS_TS = 1606824023  # 2020-12-01T12:00:23Z — same constant as fetch_fleet.py
SECONDS_PER_EPOCH = 384  # same constant as fetch_fleet.py
VALIDATOR_STAKE_ETH = 32.0
PENDING_EPOCH_SENTINEL = 10 ** 15  # same sentinel fetch_fleet.py checks activation_epoch against
DAYS_PER_YEAR = 365.25

FLEET_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "fleet.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "rewards.json")


def days_since_activation(activation_epoch, now_ts):
    if activation_epoch is None or activation_epoch >= PENDING_EPOCH_SENTINEL:
        return None
    activation_ts = GENESIS_TS + activation_epoch * SECONDS_PER_EPOCH
    return max(0.0, (now_ts - activation_ts) / 86400)


def compute_validator_rewards(v, now_ts):
    days = days_since_activation(v.get("activationEpoch"), now_ts)
    is_active = v.get("status") == "active"

    if not is_active or days is None:
        reason = (
            "not yet activated"
            if is_active
            else "status is not 'active' — balance no longer reflects lifetime reward "
                 "(exited/slashed validators withdraw to at or near 0 ETH; see script docstring)"
        )
        return {
            "index": v["index"],
            "pubkey": v["pubkey"],
            "status": v["status"],
            "daysSinceActivation": round(days, 2) if days is not None else None,
            "clRewardEth": None,
            "roiPct": None,
            "annualizedPct": None,
            "unavailableReason": reason,
        }

    cl_reward_eth = round(v["balanceEth"] - VALIDATOR_STAKE_ETH, 6)
    roi_pct = round(cl_reward_eth / VALIDATOR_STAKE_ETH * 100, 4)
    annualized_pct = (
        round((cl_reward_eth / VALIDATOR_STAKE_ETH) / days * DAYS_PER_YEAR * 100, 4)
        if days > 0
        else None
    )

    return {
        "index": v["index"],
        "pubkey": v["pubkey"],
        "status": v["status"],
        "daysSinceActivation": round(days, 2),
        "clRewardEth": cl_reward_eth,
        "roiPct": roi_pct,
        "annualizedPct": annualized_pct,
        "unavailableReason": None,
    }


def main():
    with open(FLEET_PATH) as f:
        fleet = json.load(f)

    now_ts = datetime.now(timezone.utc).timestamp()
    results = [compute_validator_rewards(v, now_ts) for v in fleet["validators"]]

    tracked = [r for r in results if r["roiPct"] is not None]
    total_cl_reward_eth = round(sum(r["clRewardEth"] for r in tracked), 6) if tracked else 0.0
    avg_roi_pct = round(sum(r["roiPct"] for r in tracked) / len(tracked), 4) if tracked else None
    annualized_tracked = [r["annualizedPct"] for r in tracked if r["annualizedPct"] is not None]
    avg_annualized_pct = (
        round(sum(annualized_tracked) / len(annualized_tracked), 4) if annualized_tracked else None
    )

    notes = [
        "beaconcha.in is NOT used anywhere in this script (its HTML validator page 403s as "
        "bot-protected, its JSON API key is zero-quota — see scripts/fetch_earnings.py's docstring "
        "for the confirmed-dead details, same finding applies here). Every figure below is computed "
        "from frontend/src/data/fleet.json's already-fetched balanceEth/activationEpoch fields — no "
        "new node or third-party call is made by this script at all.",
        "clRewardEth = balanceEth - 32.0 (the base stake). This is consensus-layer (CL) reward only — "
        "EL tips (priority fees / MEV) are paid to each validator's fee-recipient wallet, never "
        "credited to the validator's own beacon-chain balance, so this figure and earnings.json's "
        "confirmedTipsEthInScanWindow are cleanly separate, non-overlapping figures covering very "
        "different time windows (whole life since activation here, vs. a recent multi-day scan window "
        "there) — don't sum them without accounting for that.",
        "roiPct and annualizedPct are a SINCE-ACTIVATION AVERAGE, not a true trailing 7d/31d/365d APR "
        "the way the old beaconcha.in-scraped notebooks showed. annualizedPct = (clRewardEth / 32) / "
        "daysSinceActivation * 365.25 * 100 — it extrapolates the validator's whole-life average daily "
        "rate out to a year. It will NOT reflect a recent change in performance any faster than that "
        "whole-life average allows it to move; a validator active 5+ years will barely budge from a "
        "single bad (or great) recent week. A true trailing-window APR needs historical balance "
        "snapshots (balance as of 7/31/365 days ago) that this repo does not keep today — fleet.json "
        "is a single point-in-time snapshot, overwritten on every run, with no history retained. "
        "Building real trailing windows is future work (MIGRATE.md Stage 7), not approximated here.",
        "Validators with status != 'active' (exited/slashed) have every figure here set to null, not a "
        "fabricated number: an exited validator's balance drops to (or toward) 0 upon withdrawal, so "
        "'balanceEth - 32' at that point measures 'already withdrew', not lifetime reward. Pending "
        "validators (activationEpoch not yet reached, sentinel >= 10**15) are also null — there is no "
        "'since activation' window yet for them.",
        "GENESIS_TS/SECONDS_PER_EPOCH are the same constants scripts/fetch_fleet.py uses for its own "
        "daysOnline field. daysSinceActivation here is computed independently (this script has no code "
        "dependency on fetch_fleet.py, matching this repo's existing per-script constant-duplication "
        "convention) but should closely track fleet.json's own daysOnline for the same validator — a "
        "large mismatch between the two would indicate a bug in one of the two scripts, not a real "
        "difference.",
        "SAMPLE-DATA CAVEAT (same honesty convention as this repo's wallets.json/price.json): this "
        "script has no network dependency and WAS run for real against the committed fleet.json to "
        "produce this file — every number above is genuinely computed arithmetic, not hand-invented. "
        "What is NOT independently re-verified in this working session is fleet.json's own freshness: "
        "this sandbox cannot reach ethereum-wg, so fleet.json was not re-fetched from the live node "
        "before this script ran against it (see sourceFleetGeneratedAt below for exactly which "
        "fleet.json snapshot these figures are derived from). Re-run scripts/fetch_fleet.py followed "
        "immediately by this script, together, from a machine on ethereum-wg, before trusting these "
        "figures for anything beyond development/UI purposes.",
    ]

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": (
            "computed from frontend/src/data/fleet.json's balanceEth/activationEpoch fields "
            "(no live node call, no beaconcha.in call — see notes)"
        ),
        "sourceFleetGeneratedAt": fleet.get("generatedAt"),
        "baseStakeEth": VALIDATOR_STAKE_ETH,
        "fleetSummary": {
            "validatorsTracked": len(tracked),
            "validatorsTotal": len(results),
            "totalClRewardEth": total_cl_reward_eth,
            "avgRoiPct": avg_roi_pct,
            "avgAnnualizedPct": avg_annualized_pct,
        },
        "validators": results,
        "notes": notes,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    print(
        f"wrote {OUT_PATH}: {len(results)} validators, {len(tracked)} tracked, "
        f"{total_cl_reward_eth:.4f} ETH total CL reward, avg ROI {avg_roi_pct}%, "
        f"avg annualized {avg_annualized_pct}%",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
