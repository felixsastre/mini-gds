#!/usr/bin/env bash
# Runs the whole system as local processes. Ctrl-C stops all of them.
#   ./scripts/dev.sh                                  start the system
#   HOLD_SECONDS=30 uv run pytest tests/e2e          run the end-to-end tests (another terminal)
# Needs: uv, go and the Temporal CLI (brew install temporal). Ports match the e2e defaults.
set -euo pipefail
cd "$(dirname "$0")/.."

for tool in uv go temporal curl; do
  command -v "$tool" >/dev/null || { echo "missing: $tool" >&2; exit 1; }
done

HOST_PORT=18000 CACHE_PORT=18081 API_PORT=18080 TEMPORAL_PORT=17233
export TEMPORAL_ADDRESS="127.0.0.1:$TEMPORAL_PORT"
export HOST_URL="http://127.0.0.1:$HOST_PORT"
export CACHE_URL="http://127.0.0.1:$CACHE_PORT"
export HOLD_SECONDS="${HOLD_SECONDS:-900}"
export WASH_TOP=2

workdir=$(mktemp -d)
descendants() { # every process below a pid: uv starts python as a child
  local child
  for child in $(pgrep -P "$1" || true); do echo "$child"; descendants "$child"; done
}
stop_all() { # every job and every process below it
  local jobs_started=() doomed=() pid
  for pid in $(jobs -p); do jobs_started+=("$pid"); done
  for pid in "${jobs_started[@]}"; do doomed+=("$pid" $(descendants "$pid")); done # before any dies
  for pid in "${jobs_started[@]}"; do kill "$pid" 2>/dev/null || true; done # the worker loop first
  for ((i = ${#doomed[@]} - 1; i >= 0; i--)); do # last started first: temporal stops last
    kill "${doomed[i]}" 2>/dev/null || true
  done
  for _ in $(seq 10); do # a worker that cannot reach Temporal may ignore the first signal
    local alive=0
    for pid in "${doomed[@]}"; do kill -0 "$pid" 2>/dev/null && alive=1; done
    [ "$alive" = 0 ] && break
    sleep 0.3
  done
  for pid in "${doomed[@]}"; do kill -9 "$pid" 2>/dev/null || true; done
  rm -rf "$workdir"
}
trap stop_all EXIT
trap 'exit 130' INT TERM

wait_for() { # name, command that succeeds when the service is ready
  local name=$1; shift
  for _ in $(seq 60); do "$@" >/dev/null 2>&1 && return; sleep 0.5; done
  echo "$name did not start" >&2; exit 1
}

uv sync --quiet
(cd cache && go build -o "$workdir/cache" .)

temporal server start-dev --ip 127.0.0.1 --port "$TEMPORAL_PORT" --ui-port 18233 --log-level error &
uv run --no-sync uvicorn mini_gds.host:app --host 127.0.0.1 --port "$HOST_PORT" &
wait_for host curl -sf "$HOST_URL/health"

ADDR="127.0.0.1:$CACHE_PORT" TTL_SECONDS=60 "$workdir/cache" &
wait_for temporal temporal operator cluster health --address "$TEMPORAL_ADDRESS"
# Started again if it dies: the e2e tests restart it.
(while true; do uv run --no-sync python -m mini_gds.worker || true; sleep 1; done) &
uv run --no-sync uvicorn mini_gds.api:app_from_environment --factory \
  --host 127.0.0.1 --port "$API_PORT" &
wait_for api curl -sf "http://127.0.0.1:$API_PORT/health"

echo "ready: api :$API_PORT  host :$HOST_PORT  cache :$CACHE_PORT  temporal UI :18233 (Ctrl-C to stop)"
wait
