#!/usr/bin/env python3
"""Generate frontend/src/data/price.json — ETH-to-USD spot price plus total/
BTC/ETH crypto market caps, used as optional secondary (USD) figures
alongside the ETH-denominated numbers elsewhere in the dashboard and on the
Mission page's "Crypto Market Caps" section.

Ports SLC-DASHBOARD-2024/SLC/Funct.py's get_eth_price() /
get_total_crypto_market_cap() / get_BTC_market_cap() / get_eth_market_cap(),
with one deliberate change: the old get_eth_price() hardcoded a live
CoinMarketCap API key directly in source (`X-CMC_PRO_API_KEY`) — that key
must never be reused or re-hardcoded (see this repo's MIGRATE.md). Default
price source here is CoinGecko's public `/simple/price` endpoint instead,
which needs no key at all.

The three market-cap functions never used a key in the first place — checked
directly against the old source before writing this: get_total_crypto_market_cap()
called CoinGecko's public /global with no auth headers, and the two
CryptoCompare pricemultifull calls (get_BTC_market_cap/get_eth_market_cap)
had none either. Rather than add a second provider (CryptoCompare) whose
keyless-access terms are less certain going forward, all three are sourced
from CoinGecko here — /global for the total, and /simple/price's
include_market_cap flag (same call already used for the ETH spot price) for
BTC/ETH individually. Zero secrets configured, zero new providers.

CoinMarketCap remains available as an opt-in alternative source for the ETH
spot price only, but only via a freshly-issued key supplied through the
environment — never a literal default — following the same pattern as
fetch_fleet.py's BEACONCHAIN_API. Market caps always come from CoinGecko
regardless of which price source is active.

Run: python3 scripts/fetch_price.py
Env:
  COINMARKETCAP_API   optional. If set, ETH spot price is fetched from
                       CoinMarketCap instead of CoinGecko. No default value —
                       an unset/empty env var always falls back to CoinGecko.
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

COINGECKO_SIMPLE_PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=ethereum,bitcoin&vs_currencies=usd&include_market_cap=true"
)
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
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


def fetch_coingecko_simple_price():
    """One call covers ETH spot price plus BTC/ETH market caps."""
    return get_json(COINGECKO_SIMPLE_PRICE_URL)


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
    market_caps_source = "coingecko (public, no key)"
    total_crypto_market_cap_usd = None
    btc_market_cap_usd = None
    eth_market_cap_usd = None

    try:
        simple_price = fetch_coingecko_simple_price()
        coingecko_eth_usd = round(simple_price["ethereum"]["usd"], 2)
        eth_cap = simple_price["ethereum"].get("usd_market_cap")
        btc_cap = simple_price["bitcoin"].get("usd_market_cap")
        eth_market_cap_usd = round(eth_cap) if eth_cap is not None else None
        btc_market_cap_usd = round(btc_cap) if btc_cap is not None else None
    except Exception as e:
        print(f"CoinGecko simple/price fetch failed ({e.__class__.__name__}: {e})", file=sys.stderr)
        coingecko_eth_usd = None

    try:
        global_data = get_json(COINGECKO_GLOBAL_URL)
        total_cap = global_data["data"]["total_market_cap"]["usd"]
        total_crypto_market_cap_usd = round(total_cap) if total_cap is not None else None
    except Exception as e:
        print(f"CoinGecko /global fetch failed ({e.__class__.__name__}: {e})", file=sys.stderr)

    if COINMARKETCAP_API:
        try:
            eth_usd, source = fetch_from_coinmarketcap()
        except Exception as e:
            print(f"CoinMarketCap fetch failed ({e.__class__.__name__}: {e}), falling back to CoinGecko", file=sys.stderr)
            eth_usd, source = coingecko_eth_usd, "coingecko (public, no key)"
    else:
        eth_usd, source = coingecko_eth_usd, "coingecko (public, no key)"

    if eth_usd is None:
        raise RuntimeError("no ETH/USD price source succeeded (CoinGecko failed, CoinMarketCap unset or also failed)")

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "ethUsd": eth_usd,
        "marketCapsSource": market_caps_source,
        "totalCryptoMarketCapUsd": total_crypto_market_cap_usd,
        "btcMarketCapUsd": btc_market_cap_usd,
        "ethMarketCapUsd": eth_market_cap_usd,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "price.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    print(
        f"wrote {out_path}: 1 ETH = ${eth_usd:,.2f} USD (source={source}); "
        f"market caps (source={market_caps_source}): "
        f"total={total_crypto_market_cap_usd}, btc={btc_market_cap_usd}, eth={eth_market_cap_usd}"
    )


if __name__ == "__main__":
    main()
