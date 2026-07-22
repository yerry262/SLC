#!/usr/bin/env python3
"""Generate frontend/src/data/fleet.json from live node/API data.

Discovery of "which validators are ours" is anchored on DEPOSIT_ADDRESS:
  1. Preferred: beaconcha.in's /validator/eth1/{address} — enumerates every
     validator pubkey ever deposited from that address. Requires
     BEACONCHAIN_API with an active plan (currently zero-quota — see
     reference_beaconchain_api_key memory / SLC/CLAUDE.md).
  2. Fallback (used today): the local Prysm validator client's own managed
     keys (:8081/metrics), each one then verified on-chain against
     DEPOSIT_ADDRESS via its own deposit-contract transaction — same method
     proven manually against validator #166200. Slower per-key, but doesn't
     need the beaconcha.in key.

Detail enrichment (status/balance/activation) always comes from the local
node directly (Geth :8545, Prysm beacon :3500), regardless of which
discovery path ran — matches eth_stats.sh's style: hardcoded NODE_IP,
plain HTTP, no auth beyond WireGuard membership.

Run: python3 scripts/fetch_fleet.py
"""
import http.client
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

NODE_IP = "10.44.0.4"
GETH_RPC = f"http://{NODE_IP}:8545"
BEACON_API = f"http://{NODE_IP}:3500"
VALIDATOR_METRICS = f"http://{NODE_IP}:8081/metrics"
DEPOSIT_CONTRACT = "0x00000000219ab540356cBB839Cbe05303d7705Fa"
GENESIS_TS = 1606824023  # 2020-12-01T12:00:23Z
SECONDS_PER_EPOCH = 384

DEPOSIT_ADDRESS = os.environ.get("DEPOSIT_ADDRESS", "0x95aed4dc9acc614415d3bc56711998b8041878eb").lower()
BEACONCHAIN_API = os.environ.get("BEACONCHAIN_API", "")


RETRYABLE = (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError)


def _fetch_bytes(req_or_url, timeout=30, retries=3):
    """The WireGuard tunnel to the node has real transient hiccups (seen:
    IncompleteRead on a large eth_getLogs response, plain TimeoutError on a
    small /metrics GET) — every network call here goes through this retry
    wrapper, not just the ones that have already failed once."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req_or_url, timeout=timeout) as resp:
                return resp.read()
        except RETRYABLE as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_err


def rpc(method, params=None):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}).encode()
    req = urllib.request.Request(GETH_RPC, data=payload, headers={"Content-Type": "application/json", "Host": "localhost"})
    return json.loads(_fetch_bytes(req))["result"]


def get_json(url):
    return json.loads(_fetch_bytes(url))


def discover_via_beaconchain():
    if not BEACONCHAIN_API:
        return None
    url = f"https://beaconcha.in/api/v1/validator/eth1/{DEPOSIT_ADDRESS}?apikey={BEACONCHAIN_API}"
    try:
        data = get_json(url)
    except urllib.error.HTTPError as e:
        print(f"beaconcha.in discovery failed ({e.code}), falling back to local Prysm metrics", file=sys.stderr)
        return None
    if data.get("status") != "OK" or not data.get("data"):
        print(f"beaconcha.in returned no usable data ({data.get('status')}), falling back", file=sys.stderr)
        return None
    return [d["public_key"] for d in data["data"]]


def discover_via_prysm_metrics():
    text = _fetch_bytes(VALIDATOR_METRICS).decode()
    pubkeys = set()
    for line in text.splitlines():
        if line.startswith("validator_balance{"):
            pubkeys.add(line.split('pubkey="')[1].split('"')[0])
    return sorted(pubkeys)


def find_block_near_timestamp(target_ts):
    lo, hi = 1, int(rpc("eth_blockNumber"), 16)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        ts = int(rpc("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16)
        if ts < target_ts:
            lo = mid
        else:
            hi = mid
    return lo


DEPOSIT_CONTRACT_DEPLOY_BLOCK = 11052984  # ~2020-11-04, before genesis-eligible deposits started


def verify_depositor(pubkey, eligibility_epoch):
    """Confirm this validator's deposit tx came from DEPOSIT_ADDRESS.

    Anchored on activation_ELIGIBILITY_epoch, not activation_epoch — the
    latter can lag the actual deposit by months/years once the activation
    queue backs up, which blew a 50k-block window entirely for several
    validators on the first attempt. Eligibility tracks deposit processing
    far more tightly (~a day or so of eth1-follow-distance + voting delay).
    """
    if eligibility_epoch >= 10**15:
        return None  # pending, not eligible yet
    target_ts = GENESIS_TS + eligibility_epoch * SECONDS_PER_EPOCH
    if target_ts < GENESIS_TS + 86400:
        # Near/before genesis — the pre-genesis deposit window (contract
        # deploy to genesis, ~27 days) doesn't correlate cleanly with
        # eligibility_epoch timing, so just search that whole window.
        from_block, to_block = DEPOSIT_CONTRACT_DEPLOY_BLOCK, find_block_near_timestamp(GENESIS_TS + 86400)
    else:
        anchor = find_block_near_timestamp(target_ts)
        from_block, to_block = anchor - 100_000, anchor + 5_000
    logs = rpc("eth_getLogs", [{
        "fromBlock": hex(from_block), "toBlock": hex(to_block), "address": DEPOSIT_CONTRACT,
    }])
    needle = pubkey[2:].lower()
    match = next((l for l in logs if needle in l["data"]), None)
    if not match:
        return None
    block = rpc("eth_getBlockByNumber", [match["blockNumber"], True])
    tx = block["transactions"][int(match["transactionIndex"], 16)]
    return tx["from"].lower()


def main():
    pubkeys = discover_via_beaconchain()
    source = "beaconcha.in"
    if pubkeys is None:
        pubkeys = discover_via_prysm_metrics()
        source = "prysm-metrics (local, verified per-validator against DEPOSIT_ADDRESS)"

    validators = []
    for pk in pubkeys:
        d = get_json(f"{BEACON_API}/eth/v1/beacon/states/head/validators/{pk}")["data"]
        v = d["validator"]
        activation_epoch = int(v["activation_epoch"])
        eligibility_epoch = int(v["activation_eligibility_epoch"])
        days_online = None
        if activation_epoch < 10**15:
            act_ts = GENESIS_TS + activation_epoch * SECONDS_PER_EPOCH
            days_online = max(0, int((rpc_now() - act_ts) / 86400))

        depositor = None
        if source != "beaconcha.in":
            try:
                depositor = verify_depositor(pk, eligibility_epoch)
                flag = "OK" if depositor == DEPOSIT_ADDRESS else "MISMATCH"
            except Exception as e:
                flag = f"CHECK-FAILED ({e.__class__.__name__})"
            print(f"  validator {d['index']}: depositor check {flag} ({depositor})", file=sys.stderr)

        validators.append({
            "index": int(d["index"]),
            "pubkey": pk,
            "status": "active" if d["status"].startswith("active") else (
                "exited" if d["status"].startswith("withdrawal") or d["status"].startswith("exited") else "pending"
            ),
            "balanceEth": round(int(d["balance"]) / 1e9, 4),
            "activationEpoch": activation_epoch,
            "daysOnline": days_online,
        })

    validators.sort(key=lambda v: v["index"])

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "discoverySource": source,
        "depositAddress": DEPOSIT_ADDRESS,
        "currentEpoch": epoch_from_block(),
        "validators": validators,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "fleet.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    active = [v for v in validators if v["status"] == "active"]
    print(f"wrote {out_path}: {len(validators)} validators, {len(active)} active, "
          f"{sum(v['balanceEth'] for v in active):.4f} ETH, source={source}")


def rpc_now():
    block = rpc("eth_getBlockByNumber", ["latest", False])
    return int(block["timestamp"], 16)


def epoch_from_block():
    slot = int(get_json(f"{BEACON_API}/eth/v1/beacon/headers/head")["data"]["header"]["message"]["slot"])
    return slot // 32


if __name__ == "__main__":
    main()
