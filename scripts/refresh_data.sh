#!/usr/bin/env bash
# Automated data-snapshot refresh — designed to run from a systemd timer on
# the ethereum node itself (NODE_IP=localhost in that clone's .env), but works
# from any box that can reach the node's APIs (see .env.example).
#
# Runs every fetch_*.py in dependency order, then commits and pushes the
# refreshed JSON snapshot ONLY if something actually changed. A push to main
# triggers .github/workflows/deploy.yml, which rebuilds the static site with
# the new data baked in — that's the whole "live updates" pipeline; there is
# no runtime backend (see CLAUDE.md's "Data" section).
#
# Order matters: fleet.json is written first because performance, rewards,
# and (via earnings.json's feeRecipient field) wallets all read earlier
# outputs. blocks and price are independent but run in the same sequence for
# simplicity — total wall time is dominated by the eth_getLogs scans anyway.
#
# Failure policy: set -e — if any fetch script fails, abort the whole run
# with nothing committed. A partial snapshot (fresh fleet.json, stale
# performance.json) would silently misrepresent the fleet; skipping a cycle
# and letting the next timer tick retry is always safer. Each script already
# retries transient network errors internally.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Serialize runs (timer tick overlapping a slow manual run). Lock lives in
# .git so it's per-clone, works on any box, and never gets committed.
exec 9>"$REPO_ROOT/.git/refresh-data.lock"
if ! flock -n 9; then
    echo "another refresh is already running — skipping" >&2
    exit 0
fi

# Start from current main; --autostash tolerates a dirty tree from a
# previously-failed run.
git pull --rebase --autostash

for script in fetch_fleet fetch_earnings fetch_performance fetch_blocks \
              fetch_wallets fetch_price fetch_rewards; do
    echo "=== $script ==="
    python3 "$REPO_ROOT/scripts/$script.py"
done

git add frontend/src/data/*.json scripts/state/*.json

if git diff --cached --quiet; then
    echo "no data changes — nothing to commit"
    exit 0
fi

git commit -m "data: automated snapshot refresh ($(date -u '+%Y-%m-%d %H:%M UTC'))"
git push origin main
echo "pushed refreshed snapshot"
