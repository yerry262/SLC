# SLC

Dashboard tracking every Ethereum validator run on our home node — earnings, tips, uptime, and proposed/attested blocks, at a glance.

## Tech Stack

- Frontend: React + TypeScript + Vite
- Data: static JSON snapshot, refreshed by a scheduled GitHub Actions job (no live backend). Phase 1 pulls directly from our own Geth/Prysm node; phase 2 migrates to the beaconcha.in API.
- Deployment: GitHub Pages

## Live

https://yerry262.github.io/SLC

## Getting Started

```bash
cd frontend
npm install
npm run dev
```
