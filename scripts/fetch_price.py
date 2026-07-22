#!/usr/bin/env python3
"""Generate frontend/src/data/price.json — a single ETH-to-USD spot price,
used as an optional secondary (USD) figure alongside the ETH-denominated
numbers everywhere else in the dashboard.

Ports SLC-DASHBOARD-2024/SLC/Funct.py's get_eth_price(), with one
deliberate change: the old function hardcoded a live CoinMarketCap API key
directly in source (`X-CMC_PRO_API_KEY`) — that key must never be reused or
re-hardcoded (see this repo's MIGRATE.md). Default source here is
CoinGecko's public `/simple/price` endpoint, which needs no key at all, so
this script works out of the box with zero secrets configured.

CoinMarketCap remains available as an opt-in alternative source, but only
via a freshly-issued key supplied through the environment — never a
literal default — following the same pattern as fetch_fleet.py's
BEACONCHAIN_API.

Run: python3 scripts/fetch_price.py
Env:
  COINMARKETCAP_API   optional. If set, price is fetched from CoinMarketCap
                       instead of CoinGecko. No default value — an unset/empty
                       env var always falls back to CoinGecko.
"""
import http.client
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
COINMARKETCAP_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

COINMARKETCAP_API = os.environ.get("COINMARKETCAP_API", "")

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


def get_json(req_or_url, timeout=15):
    return json.loads(_fetch_bytes(req_or_url, timeout=timeout))


def fetch_from_coingecko():
    data = get_json(COINGECKO_URL)
    price = data["ethereum"]["usd"]
    return round(price, 2), "coingecko (public, no key)"


def fetch_from_coinmarketcap():
    req = urllib.request.Request(
        f"{COINMARKETCAP_URL}?symbol=ETH&convert=USD",
        headers={"Accepts": "application/json", "X-CMC_PRO_API_KEY": COINMARKETCAP_API},
    )
    data = get_json(req)
    price = data["data"]["ETH"]["quote"]["USD"]["price"]
    # Match the old notebook's round-up-to-cents behavior.
    return math.ceil(price * 100) / 100, "coinmarketcap"


def main():
    if COINMARKETCAP_API:
        try:
            eth_usd, source = fetch_from_coinmarketcap()
        except Exception as e:
            print(f"CoinMarketCap fetch failed ({e.__class__.__name__}: {e}), falling back to CoinGecko", file=sys.stderr)
            eth_usd, source = fetch_from_coingecko()
    else:
        eth_usd, source = fetch_from_coingecko()

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "ethUsd": eth_usd,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "price.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    print(f"wrote {out_path}: 1 ETH = ${eth_usd:,.2f} USD, source={source}")


if __name__ == "__main__":
    main()
