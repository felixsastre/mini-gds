#!/usr/bin/env bash
# Starts the whole system, runs the end-to-end tests against it and stops it.
#   ./scripts/e2e.sh [pytest arguments]
set -euo pipefail
cd "$(dirname "$0")/.."

log=$(mktemp)
HOLD_SECONDS=30 ./scripts/dev.sh >"$log" 2>&1 &
system=$!
trap 'kill -TERM "$system" 2>/dev/null || true; wait "$system" 2>/dev/null || true; rm -f "$log"' EXIT

# The system is ready when the worker polls: until then a reservation would just wait.
for _ in $(seq 120); do
  grep -q "worker polling task queue" "$log" && break
  kill -0 "$system" 2>/dev/null || { cat "$log" >&2; echo "the system did not start" >&2; exit 1; }
  sleep 0.5
done
grep -q "worker polling task queue" "$log" || { cat "$log" >&2; echo "the worker never polled" >&2; exit 1; }

HOLD_SECONDS=30 uv run --no-sync pytest tests/e2e "$@"
