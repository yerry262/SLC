#!/usr/bin/env python3
"""Generate frontend/src/data/performance.json from live node/API data.

Covers block-proposal and attestation performance for every validator listed
in frontend/src/data/fleet.json. Reuses fetch_fleet.py's plain-urllib,
hardcoded-NODE_IP style (see that script) — no new deps.

Data sources (all confirmed reachable/working against the live node before
this script was written):
  - Prysm validator-client metrics (:8081/metrics) — per-pubkey gauges/
    counters, only present for validators the local validator client
    actively manages (i.e. active_ongoing ones).
  - Prysm beacon REST API (:3500) — finality checkpoints, per-epoch
    attestation rewards (actual vs "ideal" for that effective-balance
    tier), per-epoch proposer duty schedules, per-slot headers (to confirm
    a scheduled proposer actually produced a block, vs missed the slot).

IMPORTANT CONSTRAINT DISCOVERED DURING TESTING (not just the earlier
research pass — re-verified live, right before writing this script):
Prysm on this node only answers beacon-state-dependent queries (proposer
duties, attestation rewards) QUICKLY for epochs within roughly the last
5-9 epochs of the current head. Anything older times out (tested up to
15s per call) because the node has to replay/regenerate archived state
that isn't cached. Concretely, against live epoch ~463239-463242:
  epoch  462239 (head)      -> proposer duties  0.2s,  rewards  1.0s
  epoch  head-5 .. head-7   -> proposer duties  ~0.4-6s, rewards ~1-2.4s (slow but OK)
  epoch  head-9 and older   -> both TIME OUT (>8-15s)
This means there is NO cheap way to query historical (e.g. lifetime)
proposal or attestation-reward data from this node's REST API — only a
narrow recent window. A full historical block-proposal count is NOT
computed here; see BLOCKS_PROPOSED_LIFETIME notes below and STATE_PATH.

Because only a recent window is queryable, this script is designed to be
run repeatedly (e.g. via CI on a schedule) and ACCUMULATE real findings
into a small persisted state file (STATE_PATH, committed to the repo)
rather than pretend to know history it can't cheaply query. Each run
extends state["scannedEpochs"] with whatever new epochs it successfully
checked this run, and appends any confirmed proposals found. The "blocks
proposed" figure in performance.json is therefore a real, source-cited,
running total *since tracking began*, never a fabricated lifetime number.

Run: python3 scripts/fetch_performance.py
"""
import http.client
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


def _load_dotenv():
    """Tiny .env loader (no new dependency) — see repo root .env.example.
    Populates os.environ from .env if present; real exported env vars still
    win (setdefault, not overwrite)."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

NODE_IP = os.environ.get("NODE_IP", "10.44.0.4")
BEACON_API = f"http://{NODE_IP}:3500"
VALIDATOR_METRICS = f"http://{NODE_IP}:8081/metrics"
SECONDS_PER_EPOCH = 384
SLOTS_PER_EPOCH = 32

SCRIPT_DIR = os.path.dirname(__file__)
FLEET_PATH = os.path.join(SCRIPT_DIR, "..", "frontend", "src", "data", "fleet.json")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "frontend", "src", "data", "performance.json")
STATE_PATH = os.path.join(SCRIPT_DIR, "state", "proposal_scan_log.json")

# How many historical calls we're willing to attempt this run for the
# proposer-duty backward scan, before giving up (each older epoch is
# progressively more likely to time out per the constraint above).
MAX_BACKWARD_PROPOSER_ATTEMPTS = 6
MAX_BACKWARD_REWARDS_ATTEMPTS = 6
FAST_TIMEOUT = 10  # seconds; calls slower than this are the "expensive/historical" ones we skip

RETRYABLE = (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError)


def _fetch_bytes(req_or_url, timeout=FAST_TIMEOUT, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req_or_url, timeout=timeout) as resp:
                return resp.read()
        except RETRYABLE as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
    raise last_err


def get_json(url, timeout=FAST_TIMEOUT):
    return json.loads(_fetch_bytes(url, timeout=timeout))


def post_json(url, body, timeout=FAST_TIMEOUT):
    payload = json.dumps(body).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    return json.loads(_fetch_bytes(req, timeout=timeout))


def load_fleet():
    with open(FLEET_PATH) as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            state = json.load(f)
            state.setdefault("confirmedMisses", [])
            return state
    return {"scannedEpochs": [], "confirmedProposals": [], "confirmedMisses": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# 1. Validator-client metrics (:8081/metrics) — attestation-vote signal +
#    a rolling participation rate anchored to process uptime (the counter
#    resets on validator-client restart, so it is NOT a lifetime total).
# ---------------------------------------------------------------------------

def parse_metrics(text):
    """Returns (process_start_ts, {pubkey: {metric: value}})"""
    process_start_ts = None
    per_pubkey = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("process_start_time_seconds "):
            process_start_ts = float(line.split()[-1])
            continue
        if "{pubkey=" not in line:
            continue
        name, rest = line.split("{", 1)
        pubkey = rest.split('pubkey="')[1].split('"')[0]
        value = float(line.rsplit(" ", 1)[-1])
        per_pubkey.setdefault(pubkey, {})[name] = value
    return process_start_ts, per_pubkey


# ---------------------------------------------------------------------------
# 2. Attestation reward effectiveness — actual vs "ideal" reward for the
#    validator's effective-balance tier, averaged over whatever recent
#    finalized epochs answer quickly.
# ---------------------------------------------------------------------------

def fetch_effective_balances(indices):
    if not indices:
        return {}
    qs = "&".join(f"id={i}" for i in indices)
    data = get_json(f"{BEACON_API}/eth/v1/beacon/states/head/validators?{qs}")["data"]
    return {int(d["index"]): int(d["validator"]["effective_balance"]) for d in data}


def fetch_attestation_rewards_epoch(epoch, indices):
    """POST rewards/attestations/{epoch}. Returns None on timeout/failure
    (treated as 'epoch not cheaply available', not an error)."""
    body = [str(i) for i in indices]
    try:
        resp = post_json(f"{BEACON_API}/eth/v1/beacon/rewards/attestations/{epoch}", body, timeout=FAST_TIMEOUT)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as e:
        print(f"  epoch {epoch}: rewards/attestations unavailable ({e.__class__.__name__})", file=sys.stderr)
        return None
    return resp["data"]


def compute_attestation_effectiveness(active_indices):
    """Returns (per_validator_pct, per_validator_gwei, epochs_sampled).

    per_validator_gwei is the REAL net attestation reward (head+target+
    source+inactivity, actual Gwei amounts from the API, can be negative)
    summed over the sampled epochs — not an estimate derived from the
    percentage. Same sampled-epoch window as the percentage figure, so
    both describe the same period."""
    fin = get_json(f"{BEACON_API}/eth/v1/beacon/states/head/finality_checkpoints")["data"]
    finalized_epoch = int(fin["finalized"]["epoch"])

    eff_bal = fetch_effective_balances(active_indices)

    sums = {i: {"actual": 0, "ideal": 0, "gwei": 0} for i in active_indices}
    epochs_sampled = []
    epoch = finalized_epoch
    attempts = 0
    while attempts < MAX_BACKWARD_REWARDS_ATTEMPTS:
        attempts += 1
        data = fetch_attestation_rewards_epoch(epoch, active_indices)
        if data is None:
            break  # this and (empirically) older epochs are the expensive/unavailable ones — stop here
        ideal_by_balance = {int(r["effective_balance"]): r for r in data["ideal_rewards"]}
        for row in data["total_rewards"]:
            idx = int(row["validator_index"])
            if idx not in sums:
                continue
            bal = eff_bal.get(idx)
            ideal = ideal_by_balance.get(bal)
            actual_gwei = int(row["head"]) + int(row["target"]) + int(row["source"]) + int(row.get("inactivity", 0))
            sums[idx]["gwei"] += actual_gwei
            if ideal is not None:
                actual_pts = int(row["head"]) + int(row["target"]) + int(row["source"])
                ideal_pts = int(ideal["head"]) + int(ideal["target"]) + int(ideal["source"])
                sums[idx]["actual"] += actual_pts
                sums[idx]["ideal"] += ideal_pts
        epochs_sampled.append(epoch)
        epoch -= 1

    pct = {}
    gwei = {}
    for idx in active_indices:
        s = sums[idx]
        pct[idx] = round(100.0 * s["actual"] / s["ideal"], 2) if s["ideal"] > 0 else None
        gwei[idx] = s["gwei"] if epochs_sampled else None
    return pct, gwei, epochs_sampled


# ---------------------------------------------------------------------------
# 3. Block-proposal check — proposer-duty schedule (cheap, 1 call/epoch,
#    32 slots) for whatever recent epochs answer quickly, cross-checked
#    against our fleet, then confirmed (not just scheduled) via a header
#    lookup on any actual hit. Findings accumulate in STATE_PATH run over run.
# ---------------------------------------------------------------------------

def fetch_proposer_duties_epoch(epoch):
    try:
        return get_json(f"{BEACON_API}/eth/v1/validator/duties/proposer/{epoch}", timeout=FAST_TIMEOUT)["data"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as e:
        print(f"  epoch {epoch}: proposer duties unavailable ({e.__class__.__name__})", file=sys.stderr)
        return None


def confirm_block_proposed(slot):
    """True if slot has an actual block header (proposer didn't miss it)."""
    try:
        get_json(f"{BEACON_API}/eth/v1/beacon/headers/{slot}", timeout=FAST_TIMEOUT)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def scan_for_proposals(fleet_index_set, current_epoch, state):
    """Walks the proposer-DUTY schedule (who was SCHEDULED), not just realized
    headers — this is the only way to attribute a MISSED slot to one of our
    validators specifically, since a missing header alone doesn't say who was
    assigned to it. Only cheap near head (see module docstring), so misses
    recorded here are real but forward-tracked-only, same limitation as
    confirmedProposals below (never a lifetime/historical claim)."""
    already_scanned = set(state["scannedEpochs"])
    new_scanned = []
    new_hits = []
    new_misses = []
    epoch = current_epoch
    attempts = 0
    while attempts < MAX_BACKWARD_PROPOSER_ATTEMPTS:
        attempts += 1
        if epoch in already_scanned:
            epoch -= 1
            continue
        duties = fetch_proposer_duties_epoch(epoch)
        if duties is None:
            break  # this and older epochs are the expensive/unavailable ones
        new_scanned.append(epoch)
        for d in duties:
            vidx = int(d["validator_index"])
            if vidx in fleet_index_set:
                slot = int(d["slot"])
                proposed = confirm_block_proposed(slot)
                print(f"  epoch {epoch} slot {slot}: our validator {vidx} scheduled, "
                      f"proposed={proposed}", file=sys.stderr)
                (new_hits if proposed else new_misses).append({"epoch": epoch, "slot": slot, "validatorIndex": vidx})
        epoch -= 1

    state["scannedEpochs"] = sorted(set(state["scannedEpochs"]) | set(new_scanned))
    existing_slots = {p["slot"] for p in state["confirmedProposals"]}
    for hit in new_hits:
        if hit["slot"] not in existing_slots:
            state["confirmedProposals"].append(hit)
    existing_miss_slots = {p["slot"] for p in state["confirmedMisses"]}
    for miss in new_misses:
        if miss["slot"] not in existing_miss_slots:
            state["confirmedMisses"].append(miss)
    return new_scanned, new_hits, new_misses


def main():
    fleet = load_fleet()
    validators = fleet["validators"]
    fleet_index_set = {v["index"] for v in validators}
    active_indices = [v["index"] for v in validators if v["status"] == "active"]

    head = get_json(f"{BEACON_API}/eth/v1/beacon/headers/head")["data"]["header"]["message"]
    current_slot = int(head["slot"])
    current_epoch = current_slot // SLOTS_PER_EPOCH

    # --- metrics (attestation-vote signal, active validators only) ---
    metrics_text = _fetch_bytes(VALIDATOR_METRICS, timeout=20).decode()
    process_start_ts, per_pubkey_metrics = parse_metrics(metrics_text)
    now_ts = time.time()
    uptime_seconds = (now_ts - process_start_ts) if process_start_ts else None
    uptime_epochs = (uptime_seconds / SECONDS_PER_EPOCH) if uptime_seconds else None

    # --- attestation reward effectiveness (recent finalized-epoch window) ---
    effectiveness_pct, reward_gwei, reward_epochs_sampled = compute_attestation_effectiveness(active_indices)
    print(f"attestation-reward effectiveness sampled over epochs {reward_epochs_sampled}", file=sys.stderr)

    # --- block proposals + misses (accumulating scan) ---
    state = load_state()
    new_scanned, new_hits, new_misses = scan_for_proposals(fleet_index_set, current_epoch, state)
    print(f"proposer-duty scan: {len(new_scanned)} new epoch(s) scanned this run "
          f"({new_scanned}), {len(new_hits)} new confirmed proposal(s), "
          f"{len(new_misses)} new confirmed miss(es)", file=sys.stderr)
    save_state(state)

    proposals_by_index = {}
    for p in state["confirmedProposals"]:
        proposals_by_index.setdefault(p["validatorIndex"], []).append(p)
    misses_by_index = {}
    for m in state["confirmedMisses"]:
        misses_by_index.setdefault(m["validatorIndex"], []).append(m)

    out_validators = []
    for v in validators:
        idx = v["index"]
        pubkey = v["pubkey"]
        m = per_pubkey_metrics.get(pubkey, {})

        successful_attestations = m.get("validator_successful_attestations")
        participation_rate_pct = None
        if successful_attestations is not None and uptime_epochs and uptime_epochs > 0:
            participation_rate_pct = round(100.0 * min(1.0, successful_attestations / uptime_epochs), 2)

        last_vote = None
        if {"validator_correctly_voted_head", "validator_correctly_voted_source", "validator_correctly_voted_target"} <= m.keys():
            last_vote = {
                "head": bool(m["validator_correctly_voted_head"]),
                "source": bool(m["validator_correctly_voted_source"]),
                "target": bool(m["validator_correctly_voted_target"]),
            }

        my_proposals = sorted(proposals_by_index.get(idx, []), key=lambda p: -p["slot"])
        my_misses = sorted(misses_by_index.get(idx, []), key=lambda p: -p["slot"])

        out_validators.append({
            "index": idx,
            "pubkey": pubkey,
            "status": v["status"],
            "blocksProposed": {
                "countTracked": len(my_proposals),
                "recentSlots": [p["slot"] for p in my_proposals[:10]],
                "lifetimeCount": None,  # not obtainable cheaply from this node — see notes
            },
            "blocksMissed": {
                "countTracked": len(my_misses),
                "recentSlots": [p["slot"] for p in my_misses[:10]],
                "trackedSince": "forward-only, near-head duty scan — see notes",
            },
            "attestation": {
                "lastVoteCorrect": last_vote,  # from most recent metrics scrape, active validators only
                "successfulAttestationsSinceProcessStart": successful_attestations,
                "participationRatePct": participation_rate_pct,
                "rewardEffectivenessPct": effectiveness_pct.get(idx),
                "rewardEthSampled": (
                    round(reward_gwei[idx] / 1e9, 9) if idx in reward_gwei and reward_gwei[idx] is not None else None
                ),
                "rewardEffectivenessEpochsSampled": reward_epochs_sampled if idx in active_indices else [],
                "inactivityScore": m.get("validator_inactivity_score"),
                "lastAttestedSlot": int(m["validator_last_attested_slot"]) if "validator_last_attested_slot" in m else None,
                "nextAttestationSlot": int(m["validator_next_attestation_slot"]) if "validator_next_attestation_slot" in m else None,
            },
        })

    out_validators.sort(key=lambda v: v["index"])

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "currentEpoch": current_epoch,
        "currentSlot": current_slot,
        "validatorClientProcessStartedAt": (
            datetime.fromtimestamp(process_start_ts, tz=timezone.utc).isoformat() if process_start_ts else None
        ),
        "proposalScan": {
            "epochsScannedTotal": len(state["scannedEpochs"]),
            "epochsScannedThisRun": new_scanned,
            "totalConfirmedProposalsTracked": len(state["confirmedProposals"]),
            "totalConfirmedMissesTracked": len(state["confirmedMisses"]),
        },
        "validators": out_validators,
        "notes": [
            "No per-validator lifetime block-proposal count exists anywhere on this node (no such "
            "metric is exposed, and the REST API has no cumulative/historical proposal endpoint). "
            "blocksProposed.lifetimeCount is null everywhere and blocksProposed.countTracked is a "
            "REAL but partial count, accumulated run-over-run in scripts/state/proposal_scan_log.json "
            "since tracking began (see proposalScan.epochsScannedTotal for exactly how much epoch "
            "history has been checked so far) — commit that state file so future CI runs keep "
            "extending coverage instead of restarting from zero.",
            "blocksMissed is the sibling of blocksProposed, same accumulating state file: a slot "
            "counts as a confirmed miss only when the proposer-duty schedule shows one of OUR "
            "validators was SCHEDULED for it and no block header exists at that slot. This is "
            "possible ONLY within this scan's near-head window (see the timing constraint above) — "
            "there is no way to attribute a historical miss to a specific validator without duty "
            "data, which is exactly the same limitation frontend/src/data/blocks.json's own notes "
            "describe for scripts/fetch_blocks.py's separate (deeper, but proposed-only) header-walk "
            "scan. blocksMissed.countTracked is real but only ever covers time since this tracking "
            "began — never treat it as a lifetime or historical miss rate.",
            "Both the proposer-duty and attestation-rewards beacon REST endpoints only answer quickly "
            "(sub-few-seconds) for epochs within roughly the last 5-9 epochs of the current chain head "
            "on this node; older epochs measurably time out (tested: 10-15s+ with no response) because "
            "Prysm has to replay/regenerate non-cached archived state. This is a real, verified "
            "limitation of this specific node's configuration, not a script bug — it is why both the "
            "proposal scan and the reward-effectiveness window below only ever cover a handful of the "
            "most recent epochs per run.",
            "attestation.rewardEffectivenessPct is actual-vs-ideal attestation reward (head+target+source "
            "points) for the validator's effective-balance tier, averaged over "
            "rewardEffectivenessEpochsSampled (a short recent finalized-epoch window, see constraint "
            "above) via POST /eth/v1/beacon/rewards/attestations/{epoch}. Only meaningful for "
            "active_ongoing validators; withdrawal_done validators show null (they earn no attestation "
            "reward once exited).",
            "attestation.rewardEthSampled is the REAL net attestation reward in ETH (head+target+source+"
            "inactivity Gwei amounts straight from the API, summed and converted — not derived from the "
            "percentage) over the exact same rewardEffectivenessEpochsSampled window above. It is a real "
            "but very short window (a handful of recent epochs, ~minutes) — do not treat it as a daily "
            "or lifetime reward rate; it is not extrapolated here.",
            "attestation.successfulAttestationsSinceProcessStart is a Prometheus COUNTER that resets on "
            "every validator-client process restart (see validatorClientProcessStartedAt) — it is NOT a "
            "lifetime total. participationRatePct divides it by elapsed epochs since that same restart, "
            "so it's a rolling rate over the current uptime window only, not the validator's full history.",
            "Metrics-derived fields (lastVoteCorrect, successfulAttestationsSinceProcessStart, "
            "inactivityScore, lastAttestedSlot, nextAttestationSlot) are only present for validators the "
            "local validator client actively manages — i.e. status == 'active' — and are null for "
            "withdrawal_done validators, which the metrics endpoint doesn't report on at all.",
        ],
    }

    with open(OUT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    print(f"wrote {OUT_PATH}: {len(out_validators)} validators, "
          f"{len(state['confirmedProposals'])} tracked proposals total, "
          f"reward effectiveness sampled over {len(reward_epochs_sampled)} epoch(s)")


if __name__ == "__main__":
    main()
