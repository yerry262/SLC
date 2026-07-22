#!/usr/bin/env python3
"""Generate frontend/src/data/wallets.json from live node data.

Ports Validator_Wallets.ipynb's "Wallet Information (Liquid)" section (see
~/CLAUDE_CORNER/SLC-DASHBOARD-2024/SLC/Validator_Wallets.ipynb): the old
notebook read eth_getBalance directly against 13 hardcoded validator
"tip jar" wallet addresses plus the deployer address (see that repo's
Varibles.py: wallet_addresses / wallet_alias, 2024-era but re-verified live
here each run). That notebook's *other* section, "Validator Information
(illiquid)" (bulk beaconcha.in validator balances), is already superseded
by fetch_fleet.py's fleet.json and is intentionally NOT re-ported here.

Unlike earnings.json's confirmedTipsEthInScanWindow (an *estimate* of
recent tip revenue, summed from block-receipt priority fees over a scan
window), this script reads the actual accumulated balance sitting in each
wallet right now — a simpler, directly-verifiable "how much have we
actually collected" figure, and it's what funds the next validator
deployment. See this repo's MIGRATE.md ("Liquid tip-jar wallet balances"
gap, Stage 6) for the full rationale.

Deliberately NOT computed or stored here: the "ETH until next 32-ETH
validator" countdown. It's a pure function of the total balance vs. the
32 ETH threshold, so it's computed client-side in WalletsPage.tsx instead —
storing it as a snapshot field would let it go stale relative to the
balance it was derived from.

Run: python3 scripts/fetch_wallets.py
Env:
  NODE_IP   home node's WireGuard address (default 10.44.0.4, same node
            fetch_fleet.py/fetch_earnings.py talk to).
"""
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

NODE_IP = os.environ.get("NODE_IP", "10.44.0.4")
GETH_RPC = f"http://{NODE_IP}:8545"

# 13 validator "tip jar" wallets + the deployer address. Public on-chain
# addresses, not secrets — safe to commit as plain constants (see this
# repo's MIGRATE.md secrets note and CLAUDE.md's DEPOSIT_ADDRESS precedent).
# Ported from the old dashboard's Varibles.py (wallet_addresses/wallet_alias);
# wallet_alias entries there were already generic labels ("Validator N Tip
# Jar", "Weekly Base Pay", "Validator Deployer"), not real names, so they're
# carried over as-is rather than replaced.
WALLET_ADDRESSES = (
    {"address": "0xbe2573005aC14262e7142731Bc70Aff8B106c33c", "alias": "Weekly Base Pay"},
    {"address": "0xeB0fFc1F050347d96a739F214761C16bF4ad7dcb", "alias": "Validator 1 Tip Jar"},
    {"address": "0xE3a725551afAEaF98837FD62729657A5A3113362", "alias": "Validator 2 Tip Jar"},
    {"address": "0xaf5DA15C219dF670acb8Eb67e461505C23fc04C1", "alias": "Validator 3 Tip Jar"},
    {"address": "0x1bbdD9733Cc44A52b7b3eEEf3ef6cA82dBE2B912", "alias": "Validator 4 Tip Jar"},
    {"address": "0x3C59c60Ab65C4B5A704EbeBF8EA397bf06dFAD8E", "alias": "Validator 5 Tip Jar"},
    {"address": "0x8d9dA7A7053049691265535573A2f572391b072C", "alias": "Validator 6 Tip Jar"},
    {"address": "0xC56b8D60B0518880fF5AAB65515b845dad89443D", "alias": "Validator 7 Tip Jar"},
    {"address": "0x143988FBf1438ff7b4404Ae3B204f8a387611eC8", "alias": "Validator 8 Tip Jar"},
    {"address": "0x107580CD8CE9A9993ACE42682aB5Cd0BCccB0517", "alias": "Validator 9 Tip Jar"},
    {"address": "0x26C4d9c0982EdC7f8fB32F428159A4ba17060A93", "alias": "Validator 10 Tip Jar"},
    {"address": "0x7fcD9a1621345Bad2E5f2b8F4385C19C30600d6d", "alias": "Validator 11 Tip Jar"},
    {"address": "0x37b08CEF6c90B6a185ef062486dC7070d09Cec36", "alias": "Validator 12 Tip Jar"},
    {"address": "0x95aed4dc9acc614415d3bc56711998b8041878eb", "alias": "Validator Deployer"},
)

RETRYABLE = (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError)


def _fetch_bytes(req_or_url, timeout=30, retries=3):
    """Same retry wrapper as fetch_fleet.py — the WireGuard tunnel to the
    node has real transient hiccups, so every network call here goes
    through this, not just ones that have already failed once."""
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
    result = json.loads(_fetch_bytes(req))
    if "error" in result:
        raise RuntimeError(f"{method} RPC error: {result['error']}")
    return result["result"]


def get_balance_eth(address):
    balance_wei_hex = rpc("eth_getBalance", [address, "latest"])
    return int(balance_wei_hex, 16) / 1e18


def main():
    wallets = []
    failures = []
    for entry in WALLET_ADDRESSES:
        address = entry["address"]
        try:
            balance_eth = get_balance_eth(address)
        except Exception as e:
            print(f"  WARNING: eth_getBalance failed for {address} ({entry['alias']}): {e}", file=sys.stderr)
            failures.append(address)
            balance_eth = None
        wallets.append({
            "address": address,
            "alias": entry["alias"],
            "balanceEth": round(balance_eth, 6) if balance_eth is not None else None,
        })

    notes = [
        "Balances are read live via eth_getBalance (Geth JSON-RPC, 'latest' block) against the node "
        "at NODE_IP over ethereum-wg — the actual current balance of each wallet, not an estimate.",
        "This is a distinct figure from earnings.json's confirmedTipsEthInScanWindow: that measures "
        "recent tip revenue over a scan window; this measures the real accumulated balance sitting in "
        "each wallet right now, which is also what funds the next 32-ETH validator deployment.",
        "The 'ETH until next validator' countdown is intentionally not included here — it's a pure "
        "function of the total balance below and is computed client-side (see WalletsPage.tsx) so it "
        "can't go stale relative to the balance snapshot it's derived from.",
    ]
    if failures:
        notes.append(f"eth_getBalance failed for {len(failures)} address(es), left as null (never guessed): "
                      f"{', '.join(failures)}.")

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "eth_getBalance (Geth JSON-RPC, 'latest') against the home node over ethereum-wg",
        "nodeSource": GETH_RPC,
        "wallets": wallets,
        "notes": notes,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "wallets.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    known = [w["balanceEth"] for w in wallets if w["balanceEth"] is not None]
    print(f"wrote {out_path}: {len(wallets)} wallets, {len(known)} with a confirmed balance, "
          f"{sum(known):.6f} ETH total, {len(failures)} failure(s)")


if __name__ == "__main__":
    main()
