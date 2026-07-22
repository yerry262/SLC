#!/usr/bin/env python3
"""Generate frontend/src/data/blocks.json — every block our validators have
ever actually proposed, discovered by walking realized beacon-chain block
headers (NOT the proposer-duty schedule).

Why headers, not duties: a REALIZED slot's header (GET
/eth/v1/beacon/headers/{slot}) permanently embeds that block's
proposer_index — it's just historical chain data, cheap to read at any
depth. The proposer-*duty* schedule (GET
/eth/v1/validator/duties/proposer/{epoch}), by contrast, requires Prysm to
regenerate archived beacon state to compute who *was scheduled* — confirmed
during this repo's earlier research (see scripts/fetch_performance.py's
docstring) to only answer quickly for the last ~5-9 epochs of head on this
node; anything older times out. That's why fetch_performance.py's
duty-based scan can only ever cover a near-head window, and why it's the
right (and only) tool for detecting MISSED slots specifically assigned to
one of our validators (state-aware, no way around it) but the wrong tool
for full lifetime PROPOSED-block history. This script does the header-walk
instead, which has no such depth limit.

Consequence for "proposed" vs "missed":
  - PROPOSED: fully knowable at any historical depth (this script).
  - MISSED (attributable to a specific one of OUR validators): only
    knowable near head, going forward from whenever tracking starts — see
    fetch_performance.py's confirmedMisses (added alongside this script).
    A slot with no header could always mean "assigned to some other
    validator among >1,000,000 active mainnet validators", not us, so an
    old missed slot can't be attributed without duty data this node can't
    cheaply produce. blocks.json is honest about this rather than guessing.

Resumability: a full walk from head back to our oldest validator's
activation slot is a genuinely large scan (millions of slots on a
multi-year-old validator) — not a single-run job. Progress is checkpointed
in STATE_PATH (committed to the repo) as a list of [from_slot, to_slot]
scanned ranges plus confirmed proposals found so far. Each run scans
SCAN_SLOTS_PER_RUN slots extending the frontier: forward from head first
(to stay current), then backward from the oldest scanned slot toward the
oldest validator's activation slot. Re-run this script (e.g. on a
schedule) until scanProgress.fullHistoryComplete is true.

Run: python3 scripts/fetch_blocks.py
Env:
  SCAN_SLOTS_PER_RUN   how many new slots to check this run (default 20000,
                       matching fetch_earnings.py's window size).
  SCAN_CONCURRENCY     parallel header fetches (default 50).
"""
import concurrent.futures
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
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
GETH_RPC = f"http://{NODE_IP}:8545"
BEACON_API = f"http://{NODE_IP}:3500"

SCRIPT_DIR = os.path.dirname(__file__)
FLEET_PATH = os.path.join(SCRIPT_DIR, "..", "frontend", "src", "data", "fleet.json")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "frontend", "src", "data", "blocks.json")
STATE_PATH = os.path.join(SCRIPT_DIR, "state", "block_history_scan_log.json")

SCAN_SLOTS_PER_RUN = int(os.environ.get("SCAN_SLOTS_PER_RUN", "20000"))
SCAN_CONCURRENCY = int(os.environ.get("SCAN_CONCURRENCY", "50"))
SLOTS_PER_EPOCH = 32

RETRYABLE = (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError)


def _fetch_bytes(req_or_url, timeout=15, retries=2):
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


def get_json(url, timeout=15):
    return json.loads(_fetch_bytes(url, timeout=timeout))


def rpc(method, params=None, timeout=30):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}).encode()
    # Geth's --http.vhosts allowlist rejects requests whose Host header isn't
    # on the list — fetch_fleet.py/fetch_wallets.py already set this; this
    # script's own first real run against the node caught that it hadn't.
    req = urllib.request.Request(GETH_RPC, data=payload, headers={"Content-Type": "application/json", "Host": "localhost"})
    result = json.loads(_fetch_bytes(req, timeout=timeout))
    if "error" in result:
        raise RuntimeError(f"{method} RPC error: {result['error']}")
    return result["result"]


def load_fleet():
    with open(FLEET_PATH) as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"scannedRanges": [], "confirmedProposals": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def merge_ranges(ranges):
    """[[from,to], ...] (inclusive) -> sorted, merged, non-overlapping."""
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [list(ranges[0])]
    for lo, hi in ranges[1:]:
        if lo <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return merged


def next_scan_range(scanned_ranges, head_slot, oldest_activation_slot, n_slots):
    """Pick the next [from, to] window to scan: forward from head first (stay
    current), else backward from the earliest already-scanned slot toward
    oldest_activation_slot. Returns None if fully covered."""
    merged = merge_ranges(scanned_ranges)
    if not merged:
        lo = max(oldest_activation_slot, head_slot - n_slots + 1)
        return lo, head_slot
    latest_covered = merged[-1][1]
    if latest_covered < head_slot:
        lo = latest_covered + 1
        hi = min(head_slot, lo + n_slots - 1)
        return lo, hi
    earliest_covered = merged[0][0]
    if earliest_covered > oldest_activation_slot:
        hi = earliest_covered - 1
        lo = max(oldest_activation_slot, hi - n_slots + 1)
        return lo, hi
    return None  # fully covered, head to oldest activation


def fetch_proposer(slot):
    try:
        d = get_json(f"{BEACON_API}/eth/v1/beacon/headers/{slot}", timeout=10)["data"]["header"]["message"]
        return slot, int(d["proposer_index"])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return slot, None  # empty/missed slot, proposer unknown from this endpoint
        return slot, None
    except Exception:
        return slot, None


def scan_range(from_slot, to_slot, our_indices):
    slots = range(from_slot, to_slot + 1)
    found = []
    checked = 0
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=SCAN_CONCURRENCY) as pool:
        for slot, proposer in pool.map(fetch_proposer, slots):
            checked += 1
            if proposer is not None and proposer in our_indices:
                found.append({"slot": slot, "validatorIndex": proposer})
                print(f"  MATCH: slot {slot} proposed by our validator {proposer}", file=sys.stderr)
            if checked % 5000 == 0:
                rate = checked / (time.time() - t0)
                print(f"  scanned {checked}/{len(slots)} slots ({rate:.0f}/s)...", file=sys.stderr)
    print(f"  range [{from_slot}, {to_slot}] done: {checked} slots in {time.time() - t0:.0f}s, "
          f"{len(found)} match(es)", file=sys.stderr)
    return found


def compute_block_el_revenue(block_number_hex, expected_fee_recipient=None):
    """Same method as fetch_earnings.py's compute_block_el_revenue — kept as
    a separate copy here rather than a shared import so each fetch_*.py
    script stays independently runnable with no cross-script dependency,
    matching this repo's existing convention (fetch_fleet.py/
    fetch_earnings.py/fetch_performance.py are each self-contained)."""
    block = rpc("eth_getBlockByNumber", [block_number_hex, False])
    receipts = rpc("eth_getBlockReceipts", [block_number_hex])
    base_fee = int(block.get("baseFeePerGas", "0x0"), 16)
    miner = block["miner"].lower()

    priority_fee_wei = 0
    for r in receipts:
        gas_used = int(r["gasUsed"], 16)
        eff_price = int(r["effectiveGasPrice"], 16)
        priority_fee_wei += (eff_price - base_fee) * gas_used

    builder_payment_note = None
    txs = block.get("transactions", [])
    if txs:
        last_receipt = next((r for r in receipts if r["transactionHash"] == txs[-1]), None)
        if last_receipt is not None and int(last_receipt["gasUsed"], 16) == 21000:
            builder_payment_note = "last tx is a plain 21000-gas transfer (possible builder payment, unverified heuristic)"

    return {
        "blockNumber": int(block_number_hex, 16),
        "miner": miner,
        "matchesExpectedFeeRecipient": (miner == expected_fee_recipient.lower()) if expected_fee_recipient else None,
        "priorityFeeRevenueEth": round(priority_fee_wei / 1e18, 9),
        "txCount": len(txs),
        "builderPaymentNote": builder_payment_note,
    }


def main():
    fleet = load_fleet()
    validators = fleet["validators"]
    our_indices = {v["index"] for v in validators}
    oldest_activation_epoch = min(v["activationEpoch"] for v in validators)
    oldest_activation_slot = oldest_activation_epoch * SLOTS_PER_EPOCH

    head_slot = int(get_json(f"{BEACON_API}/eth/v1/beacon/headers/head")["data"]["header"]["message"]["slot"])

    state = load_state()
    window = next_scan_range(state["scannedRanges"], head_slot, oldest_activation_slot, SCAN_SLOTS_PER_RUN)

    if window is None:
        print(f"already fully scanned: head {head_slot} down to oldest activation slot "
              f"{oldest_activation_slot}. Re-run periodically to stay current with new blocks.", file=sys.stderr)
        new_found = []
    else:
        from_slot, to_slot = window
        print(f"scanning slots [{from_slot}, {to_slot}] ({to_slot - from_slot + 1} slots) "
              f"for our proposals (concurrency={SCAN_CONCURRENCY})...", file=sys.stderr)
        new_found = scan_range(from_slot, to_slot, our_indices)
        state["scannedRanges"] = merge_ranges(state["scannedRanges"] + [[from_slot, to_slot]])
        existing_slots = {p["slot"] for p in state["confirmedProposals"]}
        for hit in new_found:
            if hit["slot"] not in existing_slots:
                state["confirmedProposals"].append(hit)

    # Enrich any confirmed proposal that doesn't have revenue data yet.
    validator_by_index = {v["index"]: v for v in validators}
    for p in state["confirmedProposals"]:
        if "priorityFeeRevenueEth" in p:
            continue
        try:
            block_msg = get_json(f"{BEACON_API}/eth/v2/beacon/blocks/{p['slot']}")["data"]["message"]
            exec_block_number = int(block_msg["body"]["execution_payload"]["block_number"])
            revenue = compute_block_el_revenue(hex(exec_block_number))
            p.update(revenue)
        except Exception as e:
            print(f"  WARNING: slot {p['slot']} matched but revenue lookup failed: {e}", file=sys.stderr)
            p["revenueError"] = str(e)

    save_state(state)

    merged = merge_ranges(state["scannedRanges"])
    full_history_complete = bool(merged) and merged[0][0] <= oldest_activation_slot and merged[-1][1] >= head_slot
    total_scanned = sum(hi - lo + 1 for lo, hi in merged)

    proposals_sorted = sorted(state["confirmedProposals"], key=lambda p: -p["slot"])
    total_revenue = sum(p.get("priorityFeeRevenueEth", 0) for p in proposals_sorted)

    notes = [
        "Proposed-block discovery walks realized beacon headers (GET /eth/v1/beacon/headers/{slot}) "
        "and matches each block's proposer_index against our validator set — this reads already-finalized "
        "chain data, not scheduled-duty state, so (unlike fetch_performance.py's duty scan) it works at "
        "any historical depth on this node, not just near head.",
        f"Coverage so far: {total_scanned} slot(s) scanned across {len(merged)} range(s); "
        f"fullHistoryComplete={full_history_complete}. A full walk from head ({head_slot}) back to our "
        f"oldest validator's activation slot ({oldest_activation_slot}) is a multi-million-slot job — "
        "this script is designed to be re-run repeatedly (e.g. on a schedule), extending scanProgress "
        "each time via scripts/state/block_history_scan_log.json (committed to the repo), rather than "
        "attempt it in one run.",
        "MISSED slots are intentionally NOT reported here. A header-walk can tell you a slot had no "
        "block at all, but not WHO was assigned to it — that needs the proposer-duty schedule, which "
        "(per fetch_performance.py's own documented, re-verified constraint) this node can only compute "
        "cheaply for roughly the last 5-9 epochs of head; older epochs require beacon-state regeneration "
        "that times out. So a slot missed by SOME validator among >1,000,000 active mainnet validators "
        "can't be attributed to specifically ours at historical depth — only fetch_performance.py's "
        "near-head duty scan (confirmedMisses) can honestly claim a miss was ours, and only going forward "
        "from whenever that tracking started.",
        "Each confirmed proposal's priorityFeeRevenueEth uses the same method as fetch_earnings.py: "
        "eth_getBlockReceipts, sum((effectiveGasPrice - baseFeePerGas) * gasUsed). builderPaymentNote is "
        "the same unverified 21000-gas-last-tx heuristic used there — treat revenue as priority-fee only, "
        "it may undercount true block value if a real builder payment is present.",
        "With 13 of >1,000,000 active mainnet validators, real proposal frequency for the whole fleet is "
        "roughly one every 1-2 months (confirmed empirically: fetch_earnings.py's own most recent 20000-"
        "slot/~2.8-day scan found zero) — a short list here, growing slowly as coverage extends and time "
        "passes, is the expected honest outcome, not a bug.",
    ]

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "beacon-header walk on our own node (Geth + Prysm beacon API); no beaconcha.in, no fabricated figures",
        "depositAddress": fleet.get("depositAddress"),
        "scanProgress": {
            "headSlot": head_slot,
            "oldestValidatorActivationSlot": oldest_activation_slot,
            "scannedRanges": merged,
            "slotsScannedTotal": total_scanned,
            "fullHistoryComplete": full_history_complete,
        },
        "proposals": [
            {
                "slot": p["slot"],
                "validatorIndex": p["validatorIndex"],
                "validatorPubkey": (validator_by_index.get(p["validatorIndex"]) or {}).get("pubkey"),
                "blockNumber": p.get("blockNumber"),
                "priorityFeeRevenueEth": p.get("priorityFeeRevenueEth"),
                "builderPaymentNote": p.get("builderPaymentNote"),
                "revenueError": p.get("revenueError"),
            }
            for p in proposals_sorted
        ],
        "totalConfirmedProposals": len(proposals_sorted),
        "totalPriorityFeeRevenueEth": round(total_revenue, 6),
        "notes": notes,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    print(f"wrote {OUT_PATH}: {len(proposals_sorted)} confirmed proposal(s) tracked, "
          f"{total_scanned} slot(s) scanned total, fullHistoryComplete={full_history_complete}")


if __name__ == "__main__":
    main()
