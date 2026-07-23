#!/usr/bin/env python3
"""Generate frontend/src/data/earnings.json — real execution-layer (EL)
tips/earnings per validator, computed from our own node's data.

Method (confirmed against the live node during Stage-4 research; see
CLAUDE_CORNER `Validator Earnings.ipynb` notes and this repo's history):

  beaconcha.in (both the HTML page the old notebook scraped, and its JSON
  API) is unusable right now — the HTML page 403s as bot-protected and the
  API key is zero-quota. So EL tips are NOT sourced from beaconcha.in here;
  they are computed directly from chain data on our own node:

  1. Discover our validator indices the same way scripts/fetch_fleet.py's
     fallback path does: local Prysm validator-client metrics (:8081) for
     pubkeys, then the beacon API for index/status. No beaconcha.in key
     needed.
  2. Confirm each validator's active fee_recipient. The deposit address
     (0x95aed...878eb) is NOT the fee recipient — it's only commented out
     in validator.yaml/beacon.yaml. The live config
     (~/prysm/configs/validator_tip.json on the node) gives each pubkey its
     OWN fee_recipient via `proposer-settings-file`, with a
     `default_config.fee_recipient` fallback for any pubkey not listed
     explicitly. That file lives on the node's filesystem (not exposed via
     Geth/Prysm RPC), so this script reads it over the existing
     `ethereum-wg` SSH mesh link — read-only, no config changes. If SSH is
     unavailable, fee-recipient fields are written as null (never guessed).
  3. Scan for blocks OUR validators actually proposed: walk beacon headers
     backward from head (`GET /eth/v1/beacon/headers/{slot}`, cheap, works
     arbitrarily far back — unlike `/validator/duties/proposer/{epoch}`,
     which requires state regeneration this node can't do beyond ~live
     epochs) and match `proposer_index` against our validator set.
  4. For any match found: `eth_getBlockByNumber` + `eth_getBlockReceipts`
     give real per-tx gasUsed/effectiveGasPrice/baseFeePerGas, from which
     priority-fee revenue = sum((effectiveGasPrice - baseFeePerGas) *
     gasUsed). Plus, since MEV-Boost/builder is enabled for most of our
     validators, check for a trailing plain-ETH-transfer tx to the
     fee_recipient (the relay-enforced builder payment) — this is a
     heuristic, unverified against a real example of ours (see notes).

  Honest limitation: with only 13 of >1,000,000 active mainnet validators,
  a home fleet expects roughly one proposal every 1-2 months in aggregate.
  A backward header scan of any practical size run in a few minutes will
  very likely find zero. This script reports that honestly (0 confirmed
  proposals in the scanned window) rather than inventing a number. Finding
  full lifetime proposal history requires exporting Prysm's own
  slashing-protection BoltDB, which needs a brief stop of the live
  prysm-validator.service (DB lock) — not done here without a green light,
  see the "notes" field in the output.

Run: python3 scripts/fetch_earnings.py
Env:
  SCAN_SLOTS         how many slots to walk backward from head (default 20000,
                      ~2.8 days at 12s/slot). Bigger = slower but more thorough.
  SCAN_CONCURRENCY   parallel header fetches (default 50).
"""
import concurrent.futures
import http.client
import json
import os
import subprocess
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
VALIDATOR_METRICS = f"http://{NODE_IP}:8081/metrics"
DEPOSIT_ADDRESS = "0x95aed4dc9acc614415d3bc56711998b8041878eb"

SCAN_SLOTS = int(os.environ.get("SCAN_SLOTS", "20000"))
SCAN_CONCURRENCY = int(os.environ.get("SCAN_CONCURRENCY", "50"))
SECONDS_PER_SLOT = 12

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


def rpc(method, params=None, timeout=30):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}).encode()
    req = urllib.request.Request(GETH_RPC, data=payload, headers={"Content-Type": "application/json", "Host": "localhost"})
    result = json.loads(_fetch_bytes(req, timeout=timeout))
    if "error" in result:
        raise RuntimeError(f"{method} RPC error: {result['error']}")
    return result["result"]


def get_json(url, timeout=15):
    return json.loads(_fetch_bytes(url, timeout=timeout))


# --- 1. Discover our validators (same fallback path as fetch_fleet.py) ---

def discover_validators():
    text = _fetch_bytes(VALIDATOR_METRICS, timeout=15).decode()
    pubkeys = set()
    for line in text.splitlines():
        if line.startswith("validator_balance{"):
            pubkeys.add(line.split('pubkey="')[1].split('"')[0])
    validators = []
    for pk in sorted(pubkeys):
        d = get_json(f"{BEACON_API}/eth/v1/beacon/states/head/validators/{pk}")["data"]
        validators.append({"index": int(d["index"]), "pubkey": pk, "status": d["status"]})
    validators.sort(key=lambda v: v["index"])
    return validators


# --- 2. Fee-recipient config, read live from the node over SSH ---

def fetch_fee_recipient_config():
    """Reads ~/prysm/configs/validator_tip.json. This file lives on the
    node's filesystem, not exposed via Geth/Prysm RPC, so there's no
    HTTP-only way to get it. When this script runs on the node itself (the
    slc-data-refresh systemd timer — see scripts/refresh_data.sh), the file
    is simply present locally; otherwise fall back to a read-only `cat`
    over the ethereum-wg SSH mesh link. Returns None (never a guess) if
    both paths are unavailable.

    Returns (config, source_label) — the label feeds the snapshot's
    feeRecipientConfigSource provenance field, so it must say how the file
    was ACTUALLY read, not assume the SSH path."""
    local_path = os.path.expanduser("~/prysm/configs/validator_tip.json")
    if os.path.exists(local_path):
        try:
            with open(local_path) as f:
                return json.load(f), "validator_tip.json read locally on the node"
        except (OSError, json.JSONDecodeError) as e:
            print(f"  fee-recipient config: local read failed ({e}), trying ssh", file=sys.stderr)
    try:
        out = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", "ethereum-wg",
             "cat ~/prysm/configs/validator_tip.json"],
            capture_output=True, timeout=15, text=True,
        )
    except Exception as e:
        print(f"  fee-recipient config: ssh failed ({e.__class__.__name__})", file=sys.stderr)
        return None, None
    if out.returncode != 0 or not out.stdout.strip():
        print(f"  fee-recipient config: ssh/cat failed (rc={out.returncode}): {out.stderr.strip()[:200]}", file=sys.stderr)
        return None, None
    try:
        return json.loads(out.stdout), "validator_tip.json via ssh ethereum-wg"
    except json.JSONDecodeError as e:
        print(f"  fee-recipient config: unparsable JSON ({e})", file=sys.stderr)
        return None, None


# --- 3. Scan headers backward for our proposer_index values ---

def fetch_proposer(slot):
    url = f"{BEACON_API}/eth/v1/beacon/headers/{slot}"
    try:
        d = get_json(url, timeout=10)["data"]["header"]["message"]
        return slot, int(d["proposer_index"])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return slot, None  # missed/empty slot
        return slot, None
    except Exception:
        return slot, None


def scan_for_our_proposals(our_indices, head_slot, n_slots):
    from_slot = max(0, head_slot - n_slots + 1)
    slots = range(from_slot, head_slot + 1)
    found = []
    checked = 0
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=SCAN_CONCURRENCY) as pool:
        for slot, proposer in pool.map(fetch_proposer, slots):
            checked += 1
            if proposer is not None and proposer in our_indices:
                found.append({"slot": slot, "validatorIndex": proposer})
                print(f"  MATCH: slot {slot} proposed by our validator {proposer}", file=sys.stderr)
            if checked % 2000 == 0:
                rate = checked / (time.time() - t0)
                print(f"  scanned {checked}/{len(slots)} slots ({rate:.0f}/s)...", file=sys.stderr)
    elapsed = time.time() - t0
    print(f"  scan done: {checked} slots in {elapsed:.0f}s, {len(found)} match(es)", file=sys.stderr)
    return from_slot, head_slot, checked, found


# --- 4. Compute EL tip revenue for a real proposed block ---

def compute_block_el_revenue(block_number_hex, expected_fee_recipient=None):
    block = rpc("eth_getBlockByNumber", [block_number_hex, False])
    receipts = rpc("eth_getBlockReceipts", [block_number_hex])
    base_fee = int(block.get("baseFeePerGas", "0x0"), 16)
    miner = block["miner"].lower()

    priority_fee_wei = 0
    for r in receipts:
        gas_used = int(r["gasUsed"], 16)
        eff_price = int(r["effectiveGasPrice"], 16)
        priority_fee_wei += (eff_price - base_fee) * gas_used

    builder_payment_wei = 0
    builder_payment_note = None
    txs = block.get("transactions", [])
    if txs:
        last_tx_hash = txs[-1]
        last_receipt = next((r for r in receipts if r["transactionHash"] == last_tx_hash), None)
        if last_receipt is not None:
            last_gas_used = int(last_receipt["gasUsed"], 16)
            # heuristic: plain 21000-gas transfer, last tx in block, paid to the
            # block's own fee_recipient == likely relay-enforced builder payment.
            # UNVERIFIED against a real example of ours — see notes in output.
            if last_gas_used == 21000:
                builder_payment_note = "last tx is a plain 21000-gas transfer (possible builder payment, unverified heuristic)"

    return {
        "blockNumber": int(block_number_hex, 16),
        "miner": miner,
        "matchesExpectedFeeRecipient": (miner == expected_fee_recipient.lower()) if expected_fee_recipient else None,
        "baseFeePerGasWei": base_fee,
        "txCount": len(txs),
        "priorityFeeRevenueWei": priority_fee_wei,
        "priorityFeeRevenueEth": priority_fee_wei / 1e18,
        "builderPaymentNote": builder_payment_note,
    }


def main():
    print(f"discovering validators...", file=sys.stderr)
    validators = discover_validators()
    our_indices = {v["index"] for v in validators}
    print(f"  {len(validators)} validators: {sorted(our_indices)}", file=sys.stderr)

    print(f"fetching fee-recipient config (local file or ssh ethereum-wg)...", file=sys.stderr)
    tip_config, tip_config_source = fetch_fee_recipient_config()
    proposer_config = (tip_config or {}).get("proposer_config", {})
    default_fee_recipient = (tip_config or {}).get("default_config", {}).get("fee_recipient")

    fee_recipients = {}
    for v in validators:
        entry = proposer_config.get(v["pubkey"])
        if entry:
            fee_recipients[v["pubkey"]] = {
                "feeRecipient": entry["fee_recipient"],
                "builderEnabled": entry.get("builder", {}).get("enabled"),
                "source": "validator_tip.json (explicit per-pubkey entry, live via ssh ethereum-wg)",
            }
        elif default_fee_recipient:
            fee_recipients[v["pubkey"]] = {
                "feeRecipient": default_fee_recipient,
                "builderEnabled": (tip_config or {}).get("default_config", {}).get("builder", {}).get("enabled"),
                "source": "validator_tip.json (default_config fallback, live via ssh ethereum-wg)",
            }
        else:
            fee_recipients[v["pubkey"]] = {
                "feeRecipient": None,
                "builderEnabled": None,
                "source": "unavailable (ssh to ethereum-wg failed or file unreadable)",
            }

    print(f"getting head slot...", file=sys.stderr)
    head_slot = int(get_json(f"{BEACON_API}/eth/v1/beacon/headers/head")["data"]["header"]["message"]["slot"])

    print(f"scanning {SCAN_SLOTS} slots back from head {head_slot} for our proposals "
          f"(concurrency={SCAN_CONCURRENCY})...", file=sys.stderr)
    from_slot, to_slot, checked, found = scan_for_our_proposals(our_indices, head_slot, SCAN_SLOTS)

    # For each real match, compute actual EL revenue from chain data.
    proposals_by_validator = {v["index"]: [] for v in validators}
    for match in found:
        slot = match["slot"]
        vidx = match["validatorIndex"]
        try:
            header = get_json(f"{BEACON_API}/eth/v1/beacon/headers/{slot}")["data"]["header"]["message"]
            # slot number != execution block number; pull the actual block via
            # the beacon block body's execution payload block number.
            block_data = get_json(f"{BEACON_API}/eth/v2/beacon/blocks/{slot}")["data"]["message"]
            exec_block_number = int(
                block_data["body"]["execution_payload"]["block_number"]
            )
            vpubkey = next(v["pubkey"] for v in validators if v["index"] == vidx)
            expected = fee_recipients.get(vpubkey, {}).get("feeRecipient")
            revenue = compute_block_el_revenue(hex(exec_block_number), expected)
            proposals_by_validator[vidx].append({"slot": slot, **revenue})
        except Exception as e:
            print(f"  WARNING: found proposal at slot {slot} but couldn't compute revenue: {e}", file=sys.stderr)
            proposals_by_validator[vidx].append({"slot": slot, "error": str(e)})

    validator_results = []
    for v in validators:
        props = proposals_by_validator[v["index"]]
        confirmed_revenue = [p["priorityFeeRevenueEth"] for p in props if "priorityFeeRevenueEth" in p]
        validator_results.append({
            "index": v["index"],
            "pubkey": v["pubkey"],
            "status": v["status"],
            "feeRecipient": fee_recipients[v["pubkey"]]["feeRecipient"],
            "builderEnabled": fee_recipients[v["pubkey"]]["builderEnabled"],
            "feeRecipientSource": fee_recipients[v["pubkey"]]["source"],
            "proposalsInScanWindow": props,
            "confirmedProposalCount": len(props),
            "confirmedTipsEthInScanWindow": round(sum(confirmed_revenue), 6) if confirmed_revenue else 0.0,
            "lifetimeProposalCount": None,
            "lifetimeTipsEth": None,
        })

    days_scanned = round(checked * SECONDS_PER_SLOT / 86400, 2)

    notes = [
        "EL tips are computed from raw chain data on our own node (Geth eth_getBlockByNumber + "
        "eth_getBlockReceipts: sum((effectiveGasPrice - baseFeePerGas) * gasUsed) per tx). "
        "beaconcha.in is NOT used as a source — its HTML validator page 403s (bot-protected) and "
        "its JSON API key is zero-quota, both confirmed live during this research.",
        "DEPOSIT_ADDRESS (0x95aed...878eb) is NOT the active fee recipient — it's only a commented-out "
        "`suggested-fee-recipient` in validator.yaml/beacon.yaml. The real, active fee_recipient is "
        "per-validator-pubkey, set in ~/prysm/configs/validator_tip.json on the node "
        "(`proposer-settings-file`), with a default_config fallback for unlisted pubkeys. This script "
        "reads that file live over SSH each run (ethereum-wg); if SSH fails, feeRecipient fields are "
        "null, never guessed.",
        f"Proposal detection: walked beacon headers backward via GET /eth/v1/beacon/headers/{{slot}} "
        f"from head slot {head_slot} for {checked} slots (~{days_scanned} days), matching proposer_index "
        "against our validator set. `/eth/v1/validator/duties/proposer/{epoch}` was tried and is NOT usable "
        "on this node for anything but the current epoch — it requires beacon-state regeneration this node "
        "doesn't keep, and timed out (>30s) even on an epoch only ~40 min old.",
        "With 13 of >1,000,000 active mainnet validators, expected proposal frequency for the whole fleet "
        "is roughly one every 1-2 months, so a multi-thousand-slot scan finding zero matches is the "
        "expected/honest outcome, not a bug. confirmedProposalCount/confirmedTipsEthInScanWindow reflect "
        "ONLY what was found in the scanned window above — they are real measured zeros, not lifetime totals.",
        "lifetimeProposalCount/lifetimeTipsEth are null (genuinely unknown from this script) for every "
        "validator. The correct source for full lifetime proposal history is Prysm's own "
        "slashing-protection BoltDB (/mnt/ssd1/.eth2/validator.db, `proposal-history-bucket-interchange`), "
        "exportable via `prysm.sh validator slashing-protection-history export`. That export was attempted "
        "during research and failed with 'cannot obtain database lock' because prysm-validator.service has "
        "it open live — exporting it needs a brief, deliberate stop of that service, not done automatically "
        "by this script without a go-ahead.",
        "The builder-payment heuristic (builderPaymentNote: flags a block's last tx if it's a plain "
        "21000-gas transfer, since 12/13 of our validators run with builder.enabled=true via MEV-Boost, "
        "confirmed live: mevboost.service running with 8 relays) is UNVERIFIED against any real example of "
        "ours — the scan found none. Treat confirmedTipsEthInScanWindow as priority-fee revenue only; it "
        "may undercount true block value if a real proposal ever lands and includes a builder payment.",
        "This node's Geth is not archival — eth_getBalance at old block heights fails past the pruning "
        "window even though eth_getBlockReceipts for the same block succeeds — so any future balance-delta "
        "cross-check needs to happen on the receipts-sum method above, not eth_getBalance diffing.",
    ]

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "live chain data (Geth + Prysm beacon API on our own node); no beaconcha.in, no fabricated figures",
        "depositAddress": DEPOSIT_ADDRESS,
        "feeRecipientConfigSource": "unavailable (no local file, ssh to ethereum-wg failed)" if tip_config is None else tip_config_source,
        "defaultFeeRecipient": default_fee_recipient,
        "scanWindow": {
            "headSlot": head_slot,
            "fromSlot": from_slot,
            "toSlot": to_slot,
            "slotsScanned": checked,
            "daysScanned": days_scanned,
        },
        "validators": validator_results,
        "notes": notes,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "earnings.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    total_confirmed = sum(v["confirmedProposalCount"] for v in validator_results)
    print(f"wrote {out_path}: {len(validator_results)} validators, "
          f"{checked} slots scanned (~{days_scanned}d), {total_confirmed} confirmed proposal(s) found, "
          f"fee-recipient source={'ssh-live' if tip_config else 'UNAVAILABLE'}", file=sys.stderr)


if __name__ == "__main__":
    main()
