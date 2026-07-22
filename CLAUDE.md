# SLC

## Project Overview

Dashboard for yerry's home-run Ethereum validators (on the dedicated `ethereum`
node box — `ethereum@yerry.local`, WireGuard `10.44.0.4`, alias `ethereum-wg`
from Legion; see "Ethereum node box" in `~/CLAUDE_CORNER/CLAUDE.md`). Surfaces
every validator we've operated on the `/` dashboard: earnings, tips, days
online, blocks proposed, and attestation/committee performance.

## Architecture

### Frontend
- React + TypeScript + Vite (repo-template default), deployed statically to
  GitHub Pages.

### Data — no live backend (explicitly no Railway service for this repo)
Validator data is fetched periodically by a script run in CI and baked into
the deployed site as a static JSON snapshot. The frontend reads that
snapshot at runtime — it never calls any API directly from the browser, so
no key/secret is ever shipped to the client bundle.

- **Phase 1 (now)**: data pulled directly from our own node's Geth/Prysm RPC
  over `ethereum-wg` (LAN/WireGuard-only). This means the CI job needs to run
  somewhere that can reach the mesh — plain `ubuntu-latest` cannot; needs a
  self-hosted runner (candidate: Legion or the ethereum node itself). Open
  question for planning.
- **Phase 2 (later)**: migrate the data-fetch step to beaconcha.in's API once
  the account has an active plan (`BEACONCHAIN_API` is currently zero-quota —
  see `reference_beaconchain_api_key` memory). At that point the fetch step
  can likely run on standard `ubuntu-latest` again, since beaconcha.in is
  public.

## Tech Stack

- **Frontend**: React + TypeScript + Vite
- **Backend**: none — static site; data is pre-fetched at CI build/deploy time
- **Deployment**: GitHub Pages via GitHub Actions

## Deployment Status

- **Live**: https://yerry262.github.io/SLC
- **GitHub**: https://github.com/yerry262/SLC
- **Last Deploy**: not yet deployed

## Env vars / secrets

- `DEPOSIT_ADDRESS` — our known depositor/deployer address,
  `0x95aed4dc9acc614415d3bc56711998b8041878eb`. Public on-chain info, safe to
  commit as a default/example value.
- `BEACONCHAIN_API` — beaconcha.in API key. GitHub Actions secret only,
  phase 2 — never commit the real value.

## Known Limitations

- Repo is private; GitHub Pages built from a private repo may still be
  publicly reachable at its URL depending on GitHub plan — verify visibility
  before publishing real balance/earnings figures.
- Phase 1's data source (local node) requires a CI runner that can reach the
  home mesh — needs a decision (self-hosted runner setup) before that stage
  can be built.

## Last Updated

2026-07-22
